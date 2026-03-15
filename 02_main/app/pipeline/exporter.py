import os
import re
import sys
import shutil
import tempfile
import uuid
from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

from app.pipeline.schema import JobPipelineContext

ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = Path(r"D:\03_PROJECT\00_antigravity-skills")
MATH_HWPX_SCRIPTS = SKILLS_DIR / ".agents" / "skills" / "hwpxskill-math" / "scripts"
MATH_HWPX_BASE = SKILLS_DIR / ".agents" / "skills" / "hwpxskill-math" / "templates" / "base"

if str(MATH_HWPX_SCRIPTS) not in sys.path:
    sys.path.append(str(MATH_HWPX_SCRIPTS))

from xml_primitives import (
    IDGen, STYLE, NS, SEC_NAMESPACES,
    _make_multi_run_para, _make_equation_run, make_empty_para, make_text_para
)
from exam_helpers import make_secpr_para, make_picture_para
from hwpx_utils import update_metadata, pack_hwpx, validate_hwpx


def export_hwpx(root_path: Path, job: JobPipelineContext, export_dir: Path) -> Path:
    hwpx_path = export_dir / f"{job.job_id}.hwpx"
    
    if not MATH_HWPX_BASE.exists():
        raise FileNotFoundError(f"math-hwpx base template not found at {MATH_HWPX_BASE}")

    with tempfile.TemporaryDirectory() as tmpdir_str:
        work_dir = Path(tmpdir_str) / "build"
        shutil.copytree(MATH_HWPX_BASE, work_dir)

        # 1. Process regions and generate section0.xml & collect image info
        section_path = work_dir / "Contents" / "section0.xml"
        bindata_dir = work_dir / "Contents" / "BinData"
        bindata_dir.mkdir(parents=True, exist_ok=True)
        
        images_info = _generate_section0_xml(root_path, job, section_path, bindata_dir)
        
        # 2. Update metadata using the utility from math-hwpx
        content_hpf = work_dir / "Contents" / "content.hpf"
        update_metadata(content_hpf, f"MathOCR_{job.job_id}", "MathOCR")
        
        # We must insert image manifest items manually
        _inject_images_to_manifest(content_hpf, images_info)
        
        # 3. Update header.xml with image BinData items
        header_xml_path = work_dir / "Contents" / "header.xml"
        _update_header_xml(header_xml_path, images_info)
        
        # 4. Pack HWPX using math-hwpx utility
        pack_hwpx(work_dir, hwpx_path)

    # 5. Quick structural validation
    errors = validate_hwpx(hwpx_path)
    if errors:
        raise ValueError(f"HWPX Validation failed: {errors}")

    return hwpx_path


def _parse_math_text_to_runs(idgen: IDGen, text: str, default_char_pr: int, base_unit: int = 1000) -> list:
    """Helper to split string by <math> tags and append run elements"""
    runs = []
    if not text:
        return runs
    
    parts = re.split(r"(<math>.*?</math>)", text, flags=re.DOTALL)
    for part in parts:
        if not part:
            continue
        if part.startswith("<math>") and part.endswith("</math>"):
            math_script = part[6:-7].strip()
            runs.append(_make_equation_run(idgen, math_script, default_char_pr, base_unit))
        else:
            safe_part = escape(part)
            runs.append(f'<hp:run charPrIDRef="{default_char_pr}"><hp:t>{safe_part}</hp:t></hp:run>')
    return runs


def _generate_section0_xml(root_path: Path, job: JobPipelineContext, output_path: Path, bindata_tgt_dir: Path) -> list:
    images_info = []
    idgen = IDGen()
    paras = []
    
    # Use 2-column layout via secPr
    paras.append(make_secpr_para(idgen, col_count=2, same_gap=2268))
    
    # Title
    title_runs = [f'<hp:run charPrIDRef="{STYLE["CHAR_EXAM_TITLE"]}"><hp:t>수학 분석 ({job.job_id})</hp:t></hp:run>']
    paras.append(_make_multi_run_para(idgen, title_runs, para_pr=STYLE["PARA_EXAM_TITLE"]))
    
    # Spacer
    paras.append(make_empty_para(idgen, para_pr=STYLE["PARA_HR"], char_pr=0))
    paras.append(make_empty_para(idgen))
    
    for idx, region in enumerate(sorted(job.regions, key=lambda x: x.context.order)):
        order = region.context.order
        region_id = region.context.id
        
        # 1. Image Embed (Original Cropped / SVG rendered PNG)
        # We will embed the original cropped image for analysis, or the edited SVG rendering.
        img_url = region.figure.png_rendered_url or region.figure.crop_url
        if img_url:
            src_png = root_path / img_url
            if src_png.exists():
                ext = src_png.suffix[1:].lower() or "png"
                clean_uuid = uuid.uuid4().hex
                bindata_filename = f"img_{region_id}_{clean_uuid}.{ext}"
                dest_png = bindata_tgt_dir / bindata_filename
                shutil.copy2(src_png, dest_png)
                
                bin_item_id = f"BIN_{region_id}_{clean_uuid}"
                images_info.append({"id": bin_item_id, "filename": bindata_filename, "ext": ext})
                
                # We fix width/height to reasonable exam size (e.g. 15000 HU)
                paras.append(make_picture_para(
                    idgen, bin_item_id, 
                    width_hu=25000, height_hu=15000, 
                    para_pr=STYLE["PARA_EQ"], char_pr=0
                ))
                paras.append(make_empty_para(idgen))

        # 2. OCR Text (Problem)
        ocr_text = (region.extractor.ocr_text or "").strip()
        if ocr_text:
            lines = [line for line in ocr_text.split('\n') if line.strip()]
            for i, line in enumerate(lines):
                runs = []
                if i == 0:
                    runs.append(f'<hp:run charPrIDRef="{STYLE["CHAR_EXAM_NUM"]}"><hp:t>{order}. </hp:t></hp:run>')
                runs.extend(_parse_math_text_to_runs(idgen, line, STYLE["CHAR_BODY"]))
                paras.append(_make_multi_run_para(idgen, runs, para_pr=STYLE["PARA_BODY"]))

        # 3. Explanation
        explanation = (region.extractor.explanation or "").strip()
        if explanation:
            paras.append(make_empty_para(idgen)) # Spacing
            paras.append(make_text_para(idgen, "[해설]", para_pr=STYLE["PARA_CHOICE"], char_pr=STYLE["CHAR_SUBTITLE"]))
            
            lines = [line for line in explanation.split('\n') if line.strip()]
            for line in lines:
                runs = _parse_math_text_to_runs(idgen, line, STYLE["CHAR_CHOICE"])
                paras.append(_make_multi_run_para(idgen, runs, para_pr=STYLE["PARA_CHOICE"]))

        # Blank separating lines
        paras.append(make_empty_para(idgen))
        paras.append(make_empty_para(idgen, para_pr=STYLE["PARA_HR"], char_pr=0))
        paras.append(make_empty_para(idgen))

    body_xml = "\n".join(paras)
    xml_content = f"<?xml version='1.0' encoding='UTF-8'?>\n<hs:sec {SEC_NAMESPACES}>\n  {body_xml}\n</hs:sec>"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    return images_info


def _inject_images_to_manifest(content_hpf: Path, images_info: list) -> None:
    ET.register_namespace("opf", "http://www.idpf.org/2007/opf/")
    tree = ET.parse(str(content_hpf))
    root = tree.getroot()
    ns = {"opf": "http://www.idpf.org/2007/opf/"}

    manifest_el = root.find(".//opf:manifest", ns)
    if manifest_el is not None:
        for img in images_info:
            item = ET.SubElement(manifest_el, "{http://www.idpf.org/2007/opf/}item")
            item.set("id", img["id"])
            item.set("href", f"Contents/BinData/{img['filename']}")
            item.set("media-type", f"image/{img['ext']}")
            item.set("isEmbeded", "1")

    with open(str(content_hpf), "wb") as f:
        tree.write(f, encoding="UTF-8", xml_declaration=True)


def _update_header_xml(header_xml_path: Path, images_info: list) -> None:
    ET.register_namespace("hh", "http://www.hancom.co.kr/hwpml/2011/head")
    tree = ET.parse(str(header_xml_path))
    root = tree.getroot()
    ns = {"hh": "http://www.hancom.co.kr/hwpml/2011/head"}
    
    bindata_list = root.find(".//hh:binDataList", ns)
    if bindata_list is None:
        reflist = root.find(".//hh:refList", ns)
        if reflist is not None:
            bindata_list = ET.SubElement(reflist, "{http://www.hancom.co.kr/hwpml/2011/head}binDataList")
            bindata_list.set("itemCnt", "0")
        else:
            return

    current_cnt = int(bindata_list.get("itemCnt", "0"))
    bindata_list.set("itemCnt", str(current_cnt + len(images_info)))

    for img in images_info:
        item = ET.SubElement(bindata_list, "{http://www.hancom.co.kr/hwpml/2011/head}binData")
        item.set("id", img["id"])
        item.set("extension", img["ext"])
        item.set("type", "BINA")
        item.set("format", img["ext"].upper())

    with open(str(header_xml_path), "wb") as f:
        tree.write(f, encoding="UTF-8", xml_declaration=True)
