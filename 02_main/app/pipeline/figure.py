from __future__ import annotations

import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageOps

try:
    from svg.path import parse_path as parse_svg_path
except Exception:  # pragma: no cover
    parse_svg_path = None


def normalize_image_orientation(image: Image.Image) -> Image.Image:
    """EXIF 회전을 반영한 RGB 이미지를 반환한다."""
    return ImageOps.exif_transpose(image).convert("RGB")


def read_image_size(image_bytes: bytes) -> tuple[int, int]:
    """EXIF 회전을 반영한 이미지 크기를 읽는다."""
    with Image.open(BytesIO(image_bytes)) as image:
        normalized = ImageOps.exif_transpose(image)
        return normalized.width, normalized.height


def polygon_bbox(polygon: list[list[float]], width: int, height: int) -> tuple[int, int, int, int]:
    xs = [int(round(p[0])) for p in polygon]
    ys = [int(round(p[1])) for p in polygon]
    left = max(0, min(xs))
    top = max(0, min(ys))
    right = min(width, max(xs))
    bottom = min(height, max(ys))
    if right <= left:
        right = min(width, left + 1)
    if bottom <= top:
        bottom = min(height, top + 1)
    return left, top, right, bottom


def _expand_bbox_with_padding(bbox: list[int], width: int, height: int) -> tuple[int, int, int, int]:
    """선택 영역 주변을 넉넉하게 확장한 bbox를 반환한다."""
    left, top, right, bottom = [int(value) for value in bbox]
    left = max(0, min(left, width - 1))
    top = max(0, min(top, height - 1))
    right = max(left + 1, min(right, width))
    bottom = max(top + 1, min(bottom, height))

    padding = max(8, int(round(max(right - left, bottom - top) * 0.2)))
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(width, right + padding)
    bottom = min(height, bottom + padding)
    return left, top, right, bottom


def crop_region_image(image_path: Path, polygon: list[list[float]], output_path: Path) -> bytes:
    with Image.open(image_path) as img:
        img = normalize_image_orientation(img)
        left, top, right, bottom = polygon_bbox(polygon, img.width, img.height)
        cropped = img.crop((left, top, right, bottom))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(output_path, format="PNG")
    return output_path.read_bytes()


def _trim_uniform_margins(image: Image.Image) -> Image.Image:
    """거의 흰 배경만 남은 바깥 여백을 안전하게 줄인다."""
    grayscale = ImageOps.grayscale(image)
    mask = ImageOps.invert(grayscale).point(lambda value: 255 if value > 12 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image
    left, top, right, bottom = bbox
    content_width = right - left
    content_height = bottom - top
    if content_width < image.width * 0.4 or content_height < image.height * 0.4:
        return image
    padding = 8
    return image.crop(
        (max(0, left - padding), max(0, top - padding), min(image.width, right + padding), min(image.height, bottom + padding))
    )


def _downscale_image(image: Image.Image, max_dimension: int) -> Image.Image:
    """지나치게 큰 이미지는 비율을 유지한 채 축소한다."""
    longest_side = max(image.width, image.height)
    if longest_side <= max_dimension:
        return image
    scale = max_dimension / longest_side
    resized_width = max(1, int(round(image.width * scale)))
    resized_height = max(1, int(round(image.height * scale)))
    return image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)


def preprocess_auto_full_ocr_image(image_bytes: bytes, *, preserve_geometry: bool) -> bytes:
    """자동 전체 인식용 OCR 입력 이미지를 완만하게 보정한다."""
    with Image.open(BytesIO(image_bytes)) as img:
        normalized = normalize_image_orientation(img)
        contrasted = ImageOps.autocontrast(normalized, cutoff=1)
        enhanced = ImageEnhance.Contrast(contrasted).enhance(1.08)
        processed = enhanced if preserve_geometry else _downscale_image(_trim_uniform_margins(enhanced), 2200)
        buffer = BytesIO()
        processed.save(buffer, format="PNG")
    return buffer.getvalue()


def crop_image_bytes(image_bytes: bytes, bbox: list[int], output_path: Path) -> bytes:
    """메모리 이미지 바이트에서 bbox 영역만 잘라 PNG로 저장한다."""
    with Image.open(BytesIO(image_bytes)) as img:
        img = normalize_image_orientation(img)
        left, top, right, bottom = _expand_bbox_with_padding(bbox, img.width, img.height)
        cropped = img.crop((left, top, right, bottom))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(output_path, format="PNG")
    return output_path.read_bytes()


def build_mock_svg(region_id: str, region_type: str, polygon: list[list[float]]) -> str:
    points = " ".join([f"{x},{y}" for x, y in polygon])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200">\n'
        f'  <polygon points="{points}" fill="none" stroke="#222" stroke-width="3"/>\n'
        f'  <text x="20" y="40" font-size="28">Region: {region_id} ({region_type})</text>\n'
        "</svg>\n"
    )


def normalize_svg_xml(svg_text: str) -> str:
    try:
        root = ET.fromstring(svg_text)
    except Exception as error:
        raise ValueError(f"invalid SVG XML: {error}")

    svg_ns = "http://www.w3.org/2000/svg"

    for elem in root.iter():
        local_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        elem.tag = f"{{{svg_ns}}}{local_tag}"

        for attr_name in list(elem.attrib.keys()):
            local_attr = attr_name.split("}")[-1] if "}" in attr_name else attr_name
            value = elem.attrib.pop(attr_name)
            elem.attrib[local_attr] = value

    ET.register_namespace("", svg_ns)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def sanitize_svg(svg_text: str) -> str:
    normalized = normalize_svg_xml(svg_text)
    root = ET.fromstring(normalized)

    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if tag.lower() != "svg":
        raise ValueError("root element must be <svg>")

    allowed_tags = {
        "svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan", "defs", "clipPath"
    }
    allowed_attrs = {
        "id", "x", "y", "x1", "y1", "x2", "y2", "width", "height", "rx", "ry", "cx", "cy", "r", "points", "d", "viewBox",
        "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "opacity", "fill-opacity", "stroke-opacity",
        "stroke-dasharray", "stroke-dashoffset",
        "transform", "font-family", "font-size", "font-weight", "text-anchor", "dominant-baseline", "letter-spacing", "xml:space", "xmlns", "style",
    }

    forbidden_prefixes = ("on",)
    forbidden_values = ("javascript:", "data:text/html", "http://", "https://")

    for elem in root.iter():
        elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if elem_tag not in allowed_tags:
            raise ValueError(f"disallowed SVG tag: {elem_tag}")

        for attr_name in list(elem.attrib.keys()):
            local_name = attr_name.split("}")[-1] if "}" in attr_name else attr_name
            if local_name.startswith(forbidden_prefixes):
                raise ValueError(f"disallowed SVG attribute: {local_name}")
            if local_name not in allowed_attrs and not local_name.startswith("xmlns"):
                del elem.attrib[attr_name]
                continue

            value = (elem.attrib.get(attr_name) or "").strip().lower()
            if any(token in value for token in forbidden_values):
                raise ValueError(f"disallowed SVG attribute value in {local_name}")
            if "url(" in value:
                raise ValueError(f"disallowed SVG url() in {local_name}")

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _parse_svg_number(raw: str | None, default: float = 0.0) -> float:
    if raw is None:
        return default
    value = raw.strip().lower().replace("px", "")
    try:
        return float(value)
    except Exception:
        return default


def _parse_svg_color(raw: str | None, default: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        return default
    if value.lower() == "none":
        return None
    try:
        rgb = ImageColor.getrgb(value)
        if len(rgb) == 3:
            return (rgb[0], rgb[1], rgb[2], 255)
        if len(rgb) == 4:
            return (rgb[0], rgb[1], rgb[2], rgb[3])
    except Exception:
        return default
    return default


def _parse_svg_points(value: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pair in value.strip().split():
        if "," not in pair:
            continue
        x_raw, y_raw = pair.split(",", 1)
        try:
            points.append((float(x_raw), float(y_raw)))
        except Exception:
            continue
    return points


def _svg_canvas_size(svg_root: ET.Element, scale: float = 1.0) -> tuple[int, int]:
    width = _parse_svg_number(svg_root.attrib.get("width"), 1200.0) * scale
    height = _parse_svg_number(svg_root.attrib.get("height"), 800.0) * scale

    if (width <= 0 or height <= 0) and svg_root.attrib.get("viewBox"):
        parts = (svg_root.attrib.get("viewBox") or "").replace(",", " ").split()
        if len(parts) == 4:
            width = _parse_svg_number(parts[2], width / scale) * scale
            height = _parse_svg_number(parts[3], height / scale) * scale

    width_i = max(1, min(int(round(width)), 8192))
    height_i = max(1, min(int(round(height)), 8192))
    return width_i, height_i


def _get_font(size: int):
    """Return a PIL font for Korean text rendering."""
    from PIL import ImageFont
    font_paths = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/batang.ttc",
        "C:/Windows/Fonts/gulim.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _parse_dasharray(dasharray: str, scale: float = 1.0) -> list[float]:
    """Parse SVG stroke-dasharray value into list of float lengths."""
    parts = dasharray.replace(",", " ").split()
    result: list[float] = []
    for p in parts:
        try:
            result.append(float(p) * scale)
        except ValueError:
            continue
    return result


def _draw_dashed_line(
    scale: float,
    draw: ImageDraw.ImageDraw,
    x1: float, y1: float, x2: float, y2: float,
    color: tuple[int, int, int, int],
    width: int,
    dasharray: str,
) -> None:
    """Draw a dashed line segment using the given SVG-style dasharray pattern."""
    import math
    pattern = _parse_dasharray(dasharray, scale)
    if not pattern:
        draw.line((x1, y1, x2, y2), fill=color, width=width)
        return
    # Repeat pattern to even count (dash-gap pairs)
    if len(pattern) % 2 != 0:
        pattern = pattern * 2
    total_len = math.hypot(x2 - x1, y2 - y1)
    if total_len < 1:
        return
    dx = (x2 - x1) / total_len
    dy = (y2 - y1) / total_len
    pos = 0.0
    idx = 0
    while pos < total_len:
        seg_len = pattern[idx % len(pattern)]
        end_pos = min(pos + seg_len, total_len)
        if idx % 2 == 0:  # dash
            sx = x1 + dx * pos
            sy = y1 + dy * pos
            ex = x1 + dx * end_pos
            ey = y1 + dy * end_pos
            draw.line((sx, sy, ex, ey), fill=color, width=width)
        pos = end_pos
        idx += 1


def _get_dasharray(elem) -> str:
    dash = (elem.attrib.get("stroke-dasharray") or "").strip()
    if dash: return dash
    style = (elem.attrib.get("style") or "").strip()
    if "stroke-dasharray:" in style:
        parts = style.split("stroke-dasharray:")
        if len(parts) > 1: return parts[1].split(";")[0].strip()
    return ""


def render_svg_to_png(svg_text: str, output_path: Path) -> Path:
    normalized = normalize_svg_xml(svg_text)
    root = ET.fromstring(normalized)

    SCALE = 4.0
    width, height = _svg_canvas_size(root, scale=SCALE)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def _draw_path(elem: ET.Element, dasharray: str = "") -> None:
        if parse_svg_path is None:
            return
        d = (elem.attrib.get("d") or "").strip()
        if not d:
            return

        stroke = _parse_svg_color(elem.attrib.get("stroke"), (0, 0, 0, 255))
        fill = _parse_svg_color(elem.attrib.get("fill"), None)
        stroke_w = max(1, int(round(_parse_svg_number(elem.attrib.get("stroke-width"), 1.0) * SCALE)))

        try:
            path_obj = parse_svg_path(d)
        except Exception:
            return

        subpaths: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []

        for seg in path_obj:
            name = seg.__class__.__name__.lower()
            if name == "move":
                if current:
                    subpaths.append(current)
                current = [(seg.end.real * SCALE, seg.end.imag * SCALE)]
                continue

            try:
                seg_len = float(seg.length(error=1e-2))
            except Exception:
                seg_len = 10.0
            steps = max(4, min(120, int(seg_len / 3.0) + 1))
            for i in range(steps + 1):
                point = seg.point(i / steps)
                current.append((point.real * SCALE, point.imag * SCALE))

        if current:
            subpaths.append(current)

        for points in subpaths:
            if len(points) < 2:
                continue
            if fill is not None and points[0] == points[-1]:
                draw.polygon(points, fill=fill, outline=stroke)
            if stroke is not None:
                if dasharray and dasharray.lower() != "none":
                    for i in range(len(points) - 1):
                        _draw_dashed_line(SCALE, draw, points[i][0], points[i][1], points[i+1][0], points[i+1][1], stroke, stroke_w, dasharray)
                else:
                    draw.line(points, fill=stroke, width=stroke_w)

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "line":
            x1 = _parse_svg_number(elem.attrib.get("x1")) * SCALE
            y1 = _parse_svg_number(elem.attrib.get("y1")) * SCALE
            x2 = _parse_svg_number(elem.attrib.get("x2")) * SCALE
            y2 = _parse_svg_number(elem.attrib.get("y2")) * SCALE
            stroke = _parse_svg_color(elem.attrib.get("stroke"), (0, 0, 0, 255))
            stroke_w = max(1, int(round(_parse_svg_number(elem.attrib.get("stroke-width"), 1.0) * SCALE)))
            dasharray = _get_dasharray(elem)
            if stroke is not None:
                if dasharray and dasharray.lower() != "none":
                    _draw_dashed_line(SCALE, draw, x1, y1, x2, y2, stroke, stroke_w, dasharray)
                else:
                    draw.line((x1, y1, x2, y2), fill=stroke, width=stroke_w)

        elif tag == "rect":
            x = _parse_svg_number(elem.attrib.get("x")) * SCALE
            y = _parse_svg_number(elem.attrib.get("y")) * SCALE
            w = _parse_svg_number(elem.attrib.get("width")) * SCALE
            h = _parse_svg_number(elem.attrib.get("height")) * SCALE
            fill = _parse_svg_color(elem.attrib.get("fill"), None)
            stroke = _parse_svg_color(elem.attrib.get("stroke"), (0, 0, 0, 255))
            stroke_w = max(1, int(round(_parse_svg_number(elem.attrib.get("stroke-width"), 1.0) * SCALE)))
            draw.rectangle((x, y, x + w, y + h), fill=fill, outline=stroke, width=stroke_w)

        elif tag == "circle":
            cx = _parse_svg_number(elem.attrib.get("cx")) * SCALE
            cy = _parse_svg_number(elem.attrib.get("cy")) * SCALE
            r = _parse_svg_number(elem.attrib.get("r")) * SCALE
            fill = _parse_svg_color(elem.attrib.get("fill"), None)
            stroke = _parse_svg_color(elem.attrib.get("stroke"), (0, 0, 0, 255))
            stroke_w = max(1, int(round(_parse_svg_number(elem.attrib.get("stroke-width"), 1.0) * SCALE)))
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=stroke, width=stroke_w)

        elif tag == "ellipse":
            cx = _parse_svg_number(elem.attrib.get("cx")) * SCALE
            cy = _parse_svg_number(elem.attrib.get("cy")) * SCALE
            rx = _parse_svg_number(elem.attrib.get("rx")) * SCALE
            ry = _parse_svg_number(elem.attrib.get("ry")) * SCALE
            fill = _parse_svg_color(elem.attrib.get("fill"), None)
            stroke = _parse_svg_color(elem.attrib.get("stroke"), (0, 0, 0, 255))
            stroke_w = max(1, int(round(_parse_svg_number(elem.attrib.get("stroke-width"), 1.0) * SCALE)))
            draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill, outline=stroke, width=stroke_w)

        elif tag in ("polygon", "polyline"):
            points = _parse_svg_points(elem.attrib.get("points", ""))
            if not points:
                continue
            scaled_points = [(px * SCALE, py * SCALE) for px, py in points]
            fill = _parse_svg_color(elem.attrib.get("fill"), None)
            stroke = _parse_svg_color(elem.attrib.get("stroke"), (0, 0, 0, 255))
            stroke_w = max(1, int(round(_parse_svg_number(elem.attrib.get("stroke-width"), 1.0) * SCALE)))
            if tag == "polygon":
                draw.polygon(scaled_points, fill=fill, outline=stroke)
            else:
                draw.line(scaled_points, fill=stroke, width=stroke_w)

        elif tag == "path":
            dasharray = _get_dasharray(elem)
            _draw_path(elem, dasharray)

        elif tag == "text":
            x = _parse_svg_number(elem.attrib.get("x")) * SCALE
            y = _parse_svg_number(elem.attrib.get("y")) * SCALE
            fill = _parse_svg_color(elem.attrib.get("fill"), (0, 0, 0, 255))
            font_size = max(8, int(round(_parse_svg_number(elem.attrib.get("font-size"), 16.0) * SCALE)))
            text = "".join(elem.itertext()).strip()
            if text and fill is not None:
                font = _get_font(font_size)
                draw.text((x, y - font_size), text, fill=fill, font=font)

    alpha = image.split()[-1]
    bbox = alpha.getbbox() or (0, 0, width, height)
    pad = int(8 * SCALE)
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(width, bbox[2] + pad)
    bottom = min(height, bbox[3] + pad)
    cropped = image.crop((left, top, right, bottom))
    
    # Downsample back to 1x scale for anti-aliasing
    final_width = int(cropped.width / SCALE)
    final_height = int(cropped.height / SCALE)
    if final_width > 0 and final_height > 0:
        if hasattr(Image, "Resampling"):
            resample = Image.Resampling.LANCZOS
        else:
            resample = Image.LANCZOS
        cropped = cropped.resize((final_width, final_height), resample)

    rgb = Image.new("RGB", cropped.size, (255, 255, 255))
    rgb.paste(cropped, mask=cropped.split()[-1])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(output_path, format="PNG")
    return output_path
