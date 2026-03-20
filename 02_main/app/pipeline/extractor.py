from __future__ import annotations

import base64
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

import requests

from app.config import SUPPORTED_NANO_BANANA_PROMPT_VERSIONS, get_settings
from app.pipeline.schema import ExtractorContext

logger = logging.getLogger(__name__)
SUPPORTED_STYLIZABLE_IMAGE_KINDS = {"geometry", "illustration", "generic"}
SUPPORTED_NANO_BANANA_PROVIDERS = {"vertex", "gemini_api"}
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
GEMINI_API_KEY_NOT_CONFIGURED_ERROR = "GEMINI_API_KEY is not configured"
NANO_BANANA_LOCATION_NOT_CONFIGURED_ERROR = "NANO_BANANA_LOCATION is not configured"
NANO_BANANA_MODEL_NOT_CONFIGURED_ERROR = "NANO_BANANA_MODEL is not configured"
NANO_BANANA_PROJECT_ID_NOT_CONFIGURED_ERROR = "NANO_BANANA_PROJECT_ID is not configured"
NANO_BANANA_PROMPT_VERSION_NOT_CONFIGURED_ERROR = "NANO_BANANA_PROMPT_VERSION is not configured"
NANO_BANANA_PROMPTS_DIR = Path(__file__).resolve().parent / "prompt_assets" / "nano_banana"
NANO_BANANA_PROMPT_ASSET_MISSING_ERROR = "NANO_BANANA_PROMPT_ASSET_MISSING"
NANO_BANANA_PROMPT_ASSET_EMPTY_ERROR = "NANO_BANANA_PROMPT_ASSET_EMPTY"
NANO_BANANA_PROMPT_ASSET_READ_ERROR = "NANO_BANANA_PROMPT_ASSET_READ_ERROR"


@dataclass(frozen=True)
class NanoBananaSettings:
    """Nano Banana provider별 필수 런타임 설정을 묶는다."""

    provider: str
    model: str
    prompt_version: str
    project_id: str | None = None
    location: str | None = None
    gemini_api_key: str | None = None


def _get_openai_base_url(root_path) -> str:
    """백엔드 런타임 설정에서 OpenAI base URL을 읽는다."""
    settings = get_settings(root_path)
    return settings.openai_base_url or DEFAULT_OPENAI_BASE_URL


def _get_openai_api_key(root_path) -> str:
    settings = get_settings(root_path)
    for value in (
        settings.openai_api_key,
        os.getenv("GPT52_API_KEY"),
        os.getenv("API_KEY"),
    ):
        if value:
            return value.strip()
    raise ValueError("OPENAI_API_KEY is not configured in 02_main/.env or environment variables")


def _require_setting(value: str | None, error_message: str) -> str:
    """필수 설정값이 없으면 고정 에러 문자열로 실패시킨다."""
    if value:
        return value
    raise ValueError(error_message)


def _build_vertex_nano_banana_settings(settings, model: str, prompt_version: str) -> NanoBananaSettings:
    """Vertex provider에 필요한 설정을 검증해 반환한다."""
    return NanoBananaSettings(
        provider="vertex",
        model=model,
        prompt_version=prompt_version,
        project_id=_require_setting(
            settings.nano_banana_project_id,
            NANO_BANANA_PROJECT_ID_NOT_CONFIGURED_ERROR,
        ),
        location=_require_setting(
            settings.nano_banana_location,
            NANO_BANANA_LOCATION_NOT_CONFIGURED_ERROR,
        ),
    )


def _build_gemini_api_nano_banana_settings(settings, model: str, prompt_version: str) -> NanoBananaSettings:
    """Gemini API provider에 필요한 설정을 검증해 반환한다."""
    return NanoBananaSettings(
        provider="gemini_api",
        model=model,
        prompt_version=prompt_version,
        gemini_api_key=_require_setting(
            settings.gemini_api_key,
            GEMINI_API_KEY_NOT_CONFIGURED_ERROR,
        ),
    )


def _get_nano_banana_settings(root_path) -> NanoBananaSettings:
    """Nano Banana 호출에 필요한 provider별 설정을 읽고 검증한다."""
    settings = get_settings(root_path)
    provider = settings.nano_banana_provider
    model = _require_setting(settings.nano_banana_model, NANO_BANANA_MODEL_NOT_CONFIGURED_ERROR)
    prompt_version = _require_setting(
        settings.nano_banana_prompt_version,
        NANO_BANANA_PROMPT_VERSION_NOT_CONFIGURED_ERROR,
    )
    if provider not in SUPPORTED_NANO_BANANA_PROVIDERS:
        raise ValueError(f"Unsupported NANO_BANANA_PROVIDER: {provider}")
    if provider == "vertex":
        return _build_vertex_nano_banana_settings(settings, model, prompt_version)
    return _build_gemini_api_nano_banana_settings(settings, model, prompt_version)


def _build_nano_banana_client(genai_module, settings: NanoBananaSettings):
    """Provider 설정에 맞는 google-genai Client를 생성한다."""
    if settings.provider == "vertex":
        return genai_module.Client(
            vertexai=True,
            project=settings.project_id,
            location=settings.location,
        )
    if settings.provider == "gemini_api":
        return genai_module.Client(api_key=settings.gemini_api_key)
    raise ValueError(f"Unsupported NANO_BANANA_PROVIDER: {settings.provider}")


def _normalize_stylizable_image_kind(kind: str | None) -> str:
    """Nano Banana 프롬프트용 이미지 kind 값을 정규화한다."""
    normalized = (kind or "").strip().lower()
    if normalized in SUPPORTED_STYLIZABLE_IMAGE_KINDS:
        return normalized
    return "generic"


def _raise_nano_banana_prompt_asset_error(error_code: str, asset_path: Path, error: Exception | None = None) -> None:
    """프롬프트 자산 로딩 실패를 로그와 고정 에러 문자열로 남긴다."""
    logger.error("Nano Banana prompt asset error code=%s path=%s error=%s", error_code, asset_path, error)
    raise ValueError(f"{error_code}: {asset_path}") from error


def _read_nano_banana_prompt_asset(asset_path: Path) -> str:
    """프롬프트 자산 파일을 읽고 비어 있지 않은 문자열만 반환한다."""
    if not asset_path.exists():
        _raise_nano_banana_prompt_asset_error(NANO_BANANA_PROMPT_ASSET_MISSING_ERROR, asset_path)
    try:
        content = asset_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        _raise_nano_banana_prompt_asset_error(NANO_BANANA_PROMPT_ASSET_READ_ERROR, asset_path, error)
    if content:
        return content
    _raise_nano_banana_prompt_asset_error(NANO_BANANA_PROMPT_ASSET_EMPTY_ERROR, asset_path)


def _get_nano_banana_prompt_asset_paths(version: str, kind: str) -> tuple[Path, Path, Path, Path]:
    """버전과 kind 조합에 대응하는 프롬프트 자산 경로를 반환한다."""
    version_dir = NANO_BANANA_PROMPTS_DIR / version
    return (
        version_dir / "base.txt",
        version_dir / "style.txt",
        version_dir / "kinds" / f"{kind}.txt",
        version_dir / "negative.txt",
    )


def build_nano_banana_prompt(kind: str | None, version: str) -> str:
    """버전과 kind 조합에 맞는 Nano Banana 프롬프트를 생성한다."""
    if version not in SUPPORTED_NANO_BANANA_PROMPT_VERSIONS:
        raise ValueError(f"Unsupported Nano Banana prompt version: {version}")

    resolved_kind = _normalize_stylizable_image_kind(kind)
    prompt_parts = [
        _read_nano_banana_prompt_asset(asset_path)
        for asset_path in _get_nano_banana_prompt_asset_paths(version, resolved_kind)
    ]
    return " ".join(prompt_parts)


def _extract_stylizable_image(parsed: dict) -> tuple[bool, list[int] | None, str | None]:
    """응답 JSON에서 첫 번째 변환 대상 이미지 bbox와 kind를 읽는다."""
    stylizable_images = parsed.get("stylizable_images") or []
    if not stylizable_images:
        return False, None, None

    first_image = stylizable_images[0] or {}
    bbox = first_image.get("bbox") if isinstance(first_image, dict) else None
    if not isinstance(bbox, list) or len(bbox) != 4:
        return False, None, None

    try:
        image_bbox = [int(value) for value in bbox]
    except (TypeError, ValueError):
        return False, None, None

    kind = first_image.get("kind") if isinstance(first_image, dict) else None
    return True, image_bbox, _normalize_stylizable_image_kind(kind if isinstance(kind, str) else None)


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


def analyze_region_with_gpt(
    root_path,
    crop_image_bytes: bytes,
    region_type: str,
    api_key: str | None = None,
    *,
    include_ocr: bool = True,
    include_image_detection: bool = False,
) -> dict:
    resolved_api_key = api_key or _get_openai_api_key(root_path)
    model = "gpt-5.2"
    base_url = _get_openai_base_url(root_path)

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

3. Stylizable Images
- Detect only visual elements that should become a clean exam-style image.
- Include geometry figures, illustrative drawings, and embedded problem images.
- Exclude answer choices, plain text paragraphs, tables, and chart-only layouts.
- The `kind` field must be one of `geometry`, `illustration`, or `generic`.
- Return bbox coordinates relative to the provided crop image as [left, top, right, bottom].

4. Final Output Format

Return strictly in this JSON structure:

{
  "text_blocks": ["text paragraph with inline <math>formulas</math>", "another paragraph"],
  "formulas": ["inline <math>formula1</math>", "display <math>formula2</math>"],
  "stylizable_images": [{"bbox": [0, 0, 100, 80], "kind": "geometry"}]
}

5. Important Constraints:
- Do not explain anything.
- Do not summarize.
- Do not interpret the math.
- Do not add commentary.
- Only structured extraction.

6. If a region is ambiguous:
- Prefer formula over plain text if it contains mathematical symbols.
- Prefer stylizable image over formula if it contains a geometric drawing or embedded illustration.

Now process the image."""

    prompt += (
        f" OCR enabled: {'yes' if include_ocr else 'no'}."
        f" Image detection enabled: {'yes' if include_image_detection else 'no'}."
    )

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
        headers={"Authorization": f"Bearer {resolved_api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        raise ValueError(f"OpenAI API error {response.status_code}: {response.text[:400]}")

    content = _read_chat_content(response.json())
    parsed = _extract_json_object(content)

    text_blocks = parsed.get("text_blocks") or []
    formulas = parsed.get("formulas") or []
    ocr_text = chr(10).join([str(v).strip() for v in text_blocks if str(v).strip()])
    mathml = chr(10).join([str(v).strip() for v in formulas if str(v).strip()])
    has_stylizable_image, image_bbox, image_kind = _extract_stylizable_image(parsed)

    openai_request_id = (
        response.headers.get("x-request-id")
        or response.headers.get("request-id")
        or response.headers.get("openai-request-id")
    )

    return {
        "ocr_text": ocr_text if include_ocr else "",
        "mathml": mathml if include_ocr else "",
        "has_stylizable_image": has_stylizable_image if include_image_detection else False,
        "image_bbox": image_bbox if include_image_detection else None,
        "image_kind": image_kind if include_image_detection and has_stylizable_image else None,
        "model_used": model,
        "openai_request_id": openai_request_id,
    }


def generate_explanation_with_gpt(
    root_path,
    crop_image_bytes: bytes,
    ocr_text: str,
    mathml: str,
    api_key: str | None = None,
) -> str:
    resolved_api_key = api_key or _get_openai_api_key(root_path)
    model = "gpt-5.2"
    base_url = _get_openai_base_url(root_path)

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
        headers={"Authorization": f"Bearer {resolved_api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        raise ValueError(f"OpenAI explain API error {response.status_code}: {response.text[:400]}")

    return _read_chat_content(response.json()).strip()


def generate_styled_image_with_nano_banana(
    root_path,
    image_bytes: bytes,
    *,
    model_name: str | None = None,
    prompt_kind: str | None = None,
    prompt_version: str | None = None,
) -> bytes:
    """Nano Banana 모델로 수능 스타일 이미지를 생성해 PNG 바이트를 반환한다."""
    settings = _get_nano_banana_settings(root_path)
    target_model = model_name or settings.model
    target_prompt_version = prompt_version or settings.prompt_version
    target_prompt_kind = _normalize_stylizable_image_kind(prompt_kind)
    prompt = build_nano_banana_prompt(target_prompt_kind, target_prompt_version)

    try:
        from google import genai
        from google.genai import types
    except ImportError as error:  # pragma: no cover
        raise ValueError("google-genai package is required for Nano Banana integration") from error

    logger.info(
        "Nano Banana request provider=%s model=%s prompt_version=%s prompt_kind=%s",
        settings.provider,
        target_model,
        target_prompt_version,
        target_prompt_kind,
    )

    client = _build_nano_banana_client(genai, settings)
    response = client.models.generate_content(
        model=target_model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                ],
            )
        ],
    )

    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is None:
                continue
            mime_type = getattr(inline_data, "mime_type", "") or ""
            data = getattr(inline_data, "data", None)
            if not mime_type.startswith("image/") or data is None:
                continue
            if isinstance(data, bytes):
                return data
            if isinstance(data, str):
                return base64.b64decode(data)

    raise ValueError("Nano Banana response did not contain an image")
