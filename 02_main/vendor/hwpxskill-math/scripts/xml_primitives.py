#!/usr/bin/env python3
"""Low-level XML primitives for math-hwpx section generation.

Provides:
- IDGen: sequential ID generator
- NS / SEC_NAMESPACES / SECPR_BODY: namespace and template constants
- STYLE: named constants for charPr/paraPr/borderFill IDs
- make_empty_para, make_text_para, make_equation_para, etc.
"""

from xml.sax.saxutils import escape


# ---------------------------------------------------------------------------
# STYLE constants — replaces magic numbers throughout the codebase
# ---------------------------------------------------------------------------

STYLE = {
    # charPr IDs (math_templete_example 기준)
    "CHAR_BODY": 9,               # 문제 본문
    "CHAR_TITLE": 17,             # 상단 연도/제목
    "CHAR_PROB_NUM": 18,          # 문제 번호
    "CHAR_SUBTITLE": 15,          # 해설 라벨
    "CHAR_CHOICE": 0,             # 보기/해설 본문
    "CHAR_EXAM_TITLE": 17,        # 상단 제목
    "CHAR_SUBJECT": 21,           # "수학 영역"
    "CHAR_SESSION": 20,           # 보조 헤더 문자
    "CHAR_EXAM_NUM": 18,          # 시험 문제 번호
    "CHAR_POINTS": 9,             # 배점/일반 본문
    "CHAR_PAGE_NUM": 6,           # 페이지 번호
    "CHAR_HEADER_YEAR": 17,       # 상단 연도
    "CHAR_HEADER_SUBJECT": 21,    # 상단 과목
    # paraPr IDs
    "PARA_TITLE": 9,              # 상단 연도
    "PARA_BODY": 27,              # 문제 본문
    "PARA_EQ": 11,                # 이미지/긴 수식
    "PARA_CHOICE": 11,            # 해설/추가 문단
    "PARA_EXAM_TITLE": 9,         # 상단 제목
    "PARA_SESSION": 6,            # 머리말-페이지
    "PARA_SUBJECT": 5,            # 헤드-과목
    "PARA_HCHOICE": 10,           # 보기 스타일
    "PARA_SECTION_LABEL": 11,     # 해설 라벨
    "PARA_PAGE_NUM": 0,           # 페이지 번호
    "PARA_HR": 32,                # 여백/구분
    "PARA_HEADER_YEAR": 9,        # 상단 연도
    "PARA_HEADER_SUBJECT": 5,     # 상단 과목
    "PARA_SPACER": 32,            # 빈 문단
    # borderFill IDs
    "BORDER_INVISIBLE": 2,        # 투명 테이블
}


# ---------------------------------------------------------------------------
# HWPX namespaces
# ---------------------------------------------------------------------------

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}

# All namespaces for section root
SEC_NAMESPACES = (
    'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
    'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
    'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:opf="http://www.idpf.org/2007/opf/" '
    'xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
    'xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar" '
    'xmlns:epub="http://www.idpf.org/2007/ops" '
    'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"'
)

# secPr XML template (page settings)
SECPR_BODY = (
    '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" '
    'tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" '
    'outlineShapeIDRef="1" memoShapeIDRef="0" textVerticalWidthHead="0" '
    'masterPageCnt="2">'
    '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
    '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
    '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" '
    'hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" '
    'hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
    '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
    '<hp:pagePr landscape="WIDELY" width="77102" height="111685" gutterType="LEFT_ONLY">'
    '<hp:margin header="6803" footer="2551" gutter="0" '
    'left="5385" right="5385" top="4251" bottom="7086"/>'
    '</hp:pagePr>'
    '<hp:footNotePr>'
    '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
    '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/>'
    '<hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850"/>'
    '<hp:numbering type="CONTINUOUS" newNum="1"/>'
    '<hp:placement place="EACH_COLUMN" beneathText="0"/>'
    '</hp:footNotePr>'
    '<hp:endNotePr>'
    '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
    '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000"/>'
    '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/>'
    '<hp:numbering type="CONTINUOUS" newNum="1"/>'
    '<hp:placement place="END_OF_DOCUMENT" beneathText="0"/>'
    '</hp:endNotePr>'
    '<hp:pageBorderFill type="BOTH" borderFillIDRef="9" textBorder="PAPER" '
    'headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="0" right="0" top="0" bottom="0"/>'
    '</hp:pageBorderFill>'
    '<hp:pageBorderFill type="EVEN" borderFillIDRef="1" textBorder="PAPER" '
    'headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '<hp:pageBorderFill type="ODD" borderFillIDRef="1" textBorder="PAPER" '
    'headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '<hp:masterPage idRef="masterpage0"/>'
    '<hp:masterPage idRef="masterpage1"/>'
    '</hp:secPr>'
)


# ---------------------------------------------------------------------------
# IDGen
# ---------------------------------------------------------------------------

class IDGen:
    """Sequential ID generator for HWPX elements."""
    def __init__(self, start=1000000001):
        self._next = start

    def next(self) -> str:
        val = self._next
        self._next += 1
        return str(val)

    def next_eq(self) -> str:
        """Equation-specific IDs (separate range)."""
        val = self._next
        self._next += 1
        return str(val)


# ---------------------------------------------------------------------------
# Paragraph generators
# ---------------------------------------------------------------------------

def make_empty_para(idgen: IDGen, para_pr: int = 0, char_pr: int = 0) -> str:
    """Generate an empty paragraph XML."""
    pid = idgen.next()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}"><hp:t/></hp:run>'
        f'</hp:p>'
    )


def make_text_para(idgen: IDGen, text: str, para_pr: int = 0, char_pr: int = 0) -> str:
    """Generate a text paragraph XML."""
    pid = idgen.next()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}"><hp:t>{escape(text)}</hp:t></hp:run>'
        f'</hp:p>'
    )


def _make_equation_run(idgen: IDGen, script: str, char_pr: int = STYLE["CHAR_BODY"],
                       base_unit: int = 1100) -> str:
    """Generate an inline equation <hp:run> element (no surrounding paragraph)."""
    eqid = idgen.next_eq()
    escaped_script = escape(script)
    return (
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:equation id="{eqid}" type="0" textColor="#000000" '
        f'baseUnit="{base_unit}" letterSpacing="0" lineThickness="100">'
        f'<hp:sz width="0" height="0" widthRelTo="ABS" heightRelTo="ABS"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        f'allowOverlap="0" holdAnchorAndSO="0" rgroupWithPrevCtrl="0" '
        f'vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" '
        f'vertOffset="0" horzOffset="0"/>'
        f'<hp:script>{escaped_script}</hp:script>'
        f'</hp:equation>'
        f'</hp:run>'
    )


def make_equation_para(idgen: IDGen, script: str, para_pr: int = STYLE["PARA_EQ"],
                        char_pr: int = STYLE["CHAR_BODY"], base_unit: int = 1100) -> str:
    """Generate a paragraph containing an equation."""
    pid = idgen.next()
    eq_run = _make_equation_run(idgen, script, char_pr, base_unit)
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'{eq_run}'
        f'</hp:p>'
    )


def make_text_with_equation(idgen: IDGen, text_before: str, script: str,
                             text_after: str = "", para_pr: int = STYLE["PARA_BODY"],
                             char_pr: int = STYLE["CHAR_BODY"], base_unit: int = 1100) -> str:
    """Generate a paragraph with text and inline equation mixed."""
    pid = idgen.next()
    runs = []
    if text_before:
        runs.append(f'<hp:run charPrIDRef="{char_pr}"><hp:t>{escape(text_before)}</hp:t></hp:run>')
    runs.append(_make_equation_run(idgen, script, char_pr, base_unit))
    if text_after:
        runs.append(f'<hp:run charPrIDRef="{char_pr}"><hp:t>{escape(text_after)}</hp:t></hp:run>')
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        + "".join(runs) +
        f'</hp:p>'
    )


def make_break_para(idgen: IDGen, column_break: bool = False,
                     page_break: bool = False, para_pr: int = 0) -> str:
    """Generate an empty paragraph that forces a column or page break."""
    pid = idgen.next()
    cb = "1" if column_break else "0"
    pb = "1" if page_break else "0"
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="{pb}" columnBreak="{cb}" merged="0">'
        f'<hp:run charPrIDRef="0"><hp:t/></hp:run>'
        f'</hp:p>'
    )


def _make_tab_run(char_pr: int = STYLE["CHAR_BODY"]) -> str:
    """Generate a tab character run for horizontal spacing."""
    return f'<hp:run charPrIDRef="{char_pr}"><hp:tab/></hp:run>'


def _make_multi_run_para(idgen: IDGen, runs: list, para_pr: int = 0) -> str:
    """Generate a paragraph from a list of pre-built run XML strings."""
    pid = idgen.next()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        + "".join(runs) +
        f'</hp:p>'
    )
