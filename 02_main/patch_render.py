import re

with open("app/core.py", "r", encoding="utf-8") as f:
    content = f.read()

# Make _svg_canvas_size support scale
content = content.replace("def _svg_canvas_size(svg_root: ET.Element) -> tuple[int, int]:", "def _svg_canvas_size(svg_root: ET.Element, scale: float = 1.0) -> tuple[int, int]:")
content = content.replace("width = _parse_svg_number(svg_root.attrib.get(\"width\"), 1200.0)", "width = _parse_svg_number(svg_root.attrib.get(\"width\"), 1200.0) * scale")
content = content.replace("height = _parse_svg_number(svg_root.attrib.get(\"height\"), 800.0)", "height = _parse_svg_number(svg_root.attrib.get(\"height\"), 800.0) * scale")
content = content.replace("width = _parse_svg_number(parts[2], width)", "width = _parse_svg_number(parts[2], width / scale) * scale")
content = content.replace("height = _parse_svg_number(parts[3], height)", "height = _parse_svg_number(parts[3], height / scale) * scale")
content = content.replace("width_i = max(1, min(int(round(width)), 4096))", "width_i = max(1, min(int(round(width)), 8192))")
content = content.replace("height_i = max(1, min(int(round(height)), 4096))", "height_i = max(1, min(int(round(height)), 8192))")

# Make _parse_dasharray support scale
content = content.replace("def _parse_dasharray(dasharray: str) -> list[float]:", "def _parse_dasharray(dasharray: str, scale: float = 1.0) -> list[float]:")
content = content.replace("result.append(float(p))", "result.append(float(p) * scale)")

# Make _draw_dashed_line support scale
content = content.replace("def _draw_dashed_line(", "def _draw_dashed_line(\n    scale: float,")
content = content.replace("pattern = _parse_dasharray(dasharray)", "pattern = _parse_dasharray(dasharray, scale)")

with open("app/core.py", "w", encoding="utf-8") as f:
    f.write(content)
