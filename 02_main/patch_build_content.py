import re

with open("app/core.py", "r", encoding="utf-8") as f:
    content = f.read()

old_block = """        if svg_url:
            svg_path = ROOT / svg_url
            if svg_path.exists():
                image_path = svg_path
            else:
                lines.append(f"SVG: {svg_url}")"""

new_block = """        if svg_url:
            svg_path = ROOT / svg_url
            if svg_path.exists():
                if svg_path.suffix.lower() == ".svg":
                    png_path = svg_path.with_name(f"{svg_path.stem}.export.png")
                    try:
                        _render_svg_to_png(svg_path.read_text(encoding="utf-8"), png_path)
                        image_path = png_path
                    except Exception:
                        image_path = svg_path
                else:
                    image_path = svg_path
            else:
                lines.append(f"SVG: {svg_url}")"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open("app/core.py", "w", encoding="utf-8") as f:
        f.write(content)
        print("Success")
else:
    print("Block not found")
