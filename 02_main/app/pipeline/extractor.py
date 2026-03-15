from __future__ import annotations

import base64
import json
import os
import re
from typing import Optional

import requests

from app.pipeline.schema import ExtractorContext


def _load_api_env_file(root_path) -> dict[str, str]:
    path = root_path / "apiKey.env"
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_api_setting(root_path, name: str, fallback: Optional[str] = None) -> Optional[str]:
    env_file = _load_api_env_file(root_path)
    if name in os.environ and os.environ[name].strip():
        return os.environ[name].strip()
    if name in env_file and env_file[name].strip():
        return env_file[name].strip()
    return fallback


def _get_openai_api_key(root_path) -> str:
    for key_name in ("OPENAI_API_KEY", "GPT52_API_KEY", "API_KEY"):
        value = _get_api_setting(root_path, key_name)
        if value:
            return value
    raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in apiKey.env")


def _extract_json_object(text: str) -> dict:
    value = text.strip()
    if value.startswith("```"):
        value = value.strip("`")
        value = value.replace("json", "", 1).strip()

    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", value, flags=re.DOTALL)
    if not match:
        raise ValueError("model response is not valid JSON")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model response JSON is not object")
    return parsed


def _latex_to_unicode(text: str) -> str:
    if not text:
        return text

    bs = "\\"
    superscript_map = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")
    subscript_map = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")

    text = text.replace(bs + "(", "")
    text = text.replace(bs + ")", "")
    text = text.replace(bs + "[", "")
    text = text.replace(bs + "]", "")

    overline_pattern = re.escape(bs + "overline") + r"\{([^{}]+)\}"
    frac_pattern = re.escape(bs + "frac") + r"\{([^{}]+)\}\{([^{}]+)\}"
    sqrt_pattern = re.escape(bs + "sqrt") + r"\{([^{}]+)\}"
    style_pattern = re.escape(bs) + r"(?:mathrm|text|mathbf|mathit)\{([^{}]*)\}"

    for _ in range(3):
        updated = re.sub(overline_pattern, r"\1", text)
        updated = re.sub(frac_pattern, r"\1/\2", updated)
        updated = re.sub(sqrt_pattern, r"√\1", updated)
        updated = re.sub(style_pattern, r"\1", updated)
        if updated == text:
            break
        text = updated

    replacements = [
        (bs + "therefore", "∴"),
        (bs + "because", "∵"),
        (bs + "parallel", "∥"),
        (bs + "triangle", "△"),
        (bs + "angle", "∠"),
        (bs + "times", "×"),
        (bs + "div", "÷"),
        (bs + "cdot", "·"),
        (bs + "pm", "±"),
        (bs + "mp", "∓"),
        (bs + "leq", "≤"),
        (bs + "le", "≤"),
        (bs + "geq", "≥"),
        (bs + "ge", "≥"),
        (bs + "neq", "≠"),
        (bs + "approx", "≈"),
        (bs + "equiv", "≡"),
        (bs + "infty", "∞"),
        (bs + "alpha", "α"),
        (bs + "beta", "β"),
        (bs + "gamma", "γ"),
        (bs + "theta", "θ"),
        (bs + "pi", "π"),
        (bs + "sum", "∑"),
        (bs + "int", "∫"),
        (bs + "partial", "∂"),
        (bs + "nabla", "∇"),
        (bs + "perp", "⊥"),
        (bs + "sim", "∽"),
        (bs + "circ", "°"),
        (bs + "left", ""),
        (bs + "right", ""),
    ]
    for src, dst in replacements:
        text = text.replace(src, dst)

    text = re.sub(r"\^\{?°\}?", "°", text)

    text = re.sub(
        r"\^\{([0-9+\-=()]+)\}",
        lambda m: m.group(1).translate(superscript_map),
        text,
    )
    text = re.sub(r"\^([0-9])", lambda m: m.group(1).translate(superscript_map), text)
    text = re.sub(
        r"_\{([0-9+\-=()]+)\}",
        lambda m: m.group(1).translate(subscript_map),
        text,
    )
    text = re.sub(r"_([0-9])", lambda m: m.group(1).translate(subscript_map), text)

    text = text.replace("{", "").replace("}", "")
    text = text.replace("$", "")
    text = text.replace(bs + ",", ",")
    text = text.replace(bs + ":", ":")
    text = text.replace(bs + ";", ";")
    text = text.replace(bs + "%", "%")
    text = re.sub(re.escape(bs) + r"([A-Za-z]+)", r"\1", text)

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        cleaned_lines.append(re.sub(r"[ \t]{2,}", " ", line).strip())
    return "\n".join(cleaned_lines)


def _read_chat_content(resp_json: dict) -> str:
    choices = resp_json.get("choices") or []
    if not choices:
        raise ValueError("empty model response")
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in ("text", "output_text"):
                parts.append(str(item.get("text", "")))
        return chr(10).join(parts)
    return str(content)


def analyze_region_with_gpt(root_path, crop_image_bytes: bytes, region_type: str) -> dict:
    api_key = _get_openai_api_key(root_path)
    model = "gpt-5.2"
    base_url = _get_api_setting(root_path, "OPENAI_BASE_URL", "https://api.openai.com/v1")

    image_b64 = base64.b64encode(crop_image_bytes).decode("ascii")
    image_url = f"data:image/png;base64,{image_b64}"

    prompt = r"""You are an advanced multimodal OCR and document structure parser.

Input: A single image containing:
- Plain text (Korean and/or English)
- Mathematical formulas
- Mathematical diagrams (geometry figures, graphs, coordinate systems, tables, etc.)

Your task is to:

1. Perform layout analysis.
   - Separate the image into:
     a) Text and mathematical formula regions
     b) Mathematical diagram / figure regions

2. Output rules:

A) Text and Formulas
- Extract the complete text exactly as it appears in the image.
- Preserve line breaks.
- Convert all mathematical formulas, numbers, and symbols into "Hancom Office Equation Script (HWP Equation Script)" syntax.
- STRICTLY wrap all HWP Equation Script formulas within `<math>...</math>` tags.
- For example: `<math>2x + 3 = 7</math>`, or `<math>{x+1} over {x-1}</math>`, or `<math>sqrt {b^2 - 4ac}</math>`.
- Do NOT use LaTeX syntax (e.g., no $...$, no \(...\), no \[...\], no \angle, no \circ, no \frac).
- Do NOT separate formulas from the main text; output them seamlessly inline.


C) Mathematical Diagrams
- Reconstruct diagrams structurally.
- Output as valid standalone SVG.
- Use:
    <svg xmlns="http://www.w3.org/2000/svg">
- Represent:
    - Lines as <line>
    - Circles as <circle>
    - Polygons as <polygon>
    - Paths as <path>
    - Text labels as <text>
- Maintain approximate geometry proportions.
- Do not rasterize images.
- Do not embed base64 images.
- The SVG must be editable vector format.

3. Final Output Format

Return strictly in this JSON structure:

{
  "text_blocks": ["text paragraph with inline <math>formulas</math>", "another paragraph"],
  "formulas": ["inline <math>formula1</math>", "display <math>formula2</math>"],
  "diagrams": ["<svg>...</svg>", "<svg>...</svg>"]
}

4. Important Constraints:
- Do not explain anything.
- Do not summarize.
- Do not interpret the math.
- Do not add commentary.
- Only structured extraction.

5. If a region is ambiguous:
- Prefer formula over plain text if it contains mathematical symbols.
- Prefer diagram over formula if it includes geometric shapes.

Now process the image."""

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Return strict JSON object only."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt + " Region type hint: " + region_type},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    }

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        raise ValueError(f"OpenAI API error {response.status_code}: {response.text[:400]}")

    content = _read_chat_content(response.json())
    parsed = _extract_json_object(content)

    text_blocks = parsed.get("text_blocks") or []
    formulas = parsed.get("formulas") or []
    diagrams = parsed.get("diagrams") or []

    ocr_text = chr(10).join([str(v).strip() for v in text_blocks if str(v).strip()])
    mathml = chr(10).join([str(v).strip() for v in formulas if str(v).strip()])
    diagram_svg = str(diagrams[0]).strip() if diagrams else ""

    openai_request_id = (
        response.headers.get("x-request-id")
        or response.headers.get("request-id")
        or response.headers.get("openai-request-id")
    )

    return {
        "ocr_text": ocr_text,
        "mathml": mathml,
        "diagram_svg": diagram_svg,
        "model_used": model,
        "openai_request_id": openai_request_id,
    }


def generate_explanation_with_gpt(root_path, crop_image_bytes: bytes, ocr_text: str, mathml: str) -> str:
    api_key = _get_openai_api_key(root_path)
    model = "gpt-5.2"
    base_url = _get_api_setting(root_path, "OPENAI_BASE_URL", "https://api.openai.com/v1")

    image_b64 = base64.b64encode(crop_image_bytes).decode("ascii")
    image_url = f"data:image/png;base64,{image_b64}"

    prompt = (
        "Write a concise Korean math solution explanation from OCR text and image context. "
        "Provide 4-8 sentences with key solving steps. "
        "Convert all mathematical formulas, numbers, and symbols into 'Hancom Office Equation Script (HWP Equation Script)' syntax, and strictly wrap them within `<math>...</math>` tags. "
        "For example: `<math>2x + 3 = 7</math>`. Do NOT use LaTeX syntax, including $...$ and LaTeX-style inline/display delimiters.\n"
        "Output ONLY the Korean explanation text.\n"
        + "OCR text: " + (ocr_text or "") + "\n"
        + "MathML: " + (mathml or "")
    )

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "Output plain Korean explanation text only."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    }

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        raise ValueError(f"OpenAI explain API error {response.status_code}: {response.text[:400]}")

    return _read_chat_content(response.json()).strip()
