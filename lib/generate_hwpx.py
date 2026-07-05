"""
HWPX 공공행정문서 생성기 v3
=============================
실제 행정안전부 공문서 HWPX 파일을 XML 레벨에서 분석하여 추출한 서식을 적용.

핵심 레이아웃 (실제 공문서 동일):
  - 제목: 1×1 표, 연하늘색(#DFEAF5) 배경, 하단/우측 굵은선, 20pt HY헤드라인M
  - 대제목(Ⅰ.): 1×3 표 [남색(#003366) 박스 + 빈 간격 + 하단남색밑줄 제목]
    - 셀1: #003366 배경, 15pt bold 맑은 고딕 흰색 로마숫자
    - 셀2: 빈 간격 (투명)
    - 셀3: 하단에 남색(#315F97) 밑줄, 16pt HY헤드라인M 제목
  - 중제목(□): 16pt HY헤드라인M, 양쪽정렬
  - 본문(○): 15pt 휴먼명조, 양쪽정렬, 줄간격 160%
  - 하위(-): 15pt 휴먼명조
  - 표 헤더: 12pt bold 맑은 고딕 가운데
  - 표 본문: 12pt 맑은 고딕 가운데
  - 주석(※): 12pt 맑은 고딕
  - 메타: 13pt 휴먼명조

설치: pip install python-hwpx lxml
"""
import sys, os, copy, zipfile, tempfile
from datetime import datetime

try:
    from hwpx import HwpxDocument
except ImportError:
    print("python-hwpx 미설치. pip install python-hwpx")
    sys.exit(1)

from lxml import etree

# ── 네임스페이스 ─────────────────────────────────────────────────────
HH = 'http://www.hancom.co.kr/hwpml/2011/head'
HC = 'http://www.hancom.co.kr/hwpml/2011/core'
HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'

# ── 표준 번호체계 ────────────────────────────────────────────────────
NUM_L1 = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ"]
NUM_L2 = [str(i) for i in range(1, 20)]
NUM_L3 = ["가", "나", "다", "라", "마", "바", "사", "아"]

# ── 공공 불릿 기호 ───────────────────────────────────────────────────
BULLET_H2 = "□"
BULLET_L1 = "○"
BULLET_L2 = "-"

# ── 문서 규격 ────────────────────────────────────────────────────────
DOC_TEXT_WIDTH = 42520

# ── 색상 (실제 행안부 문서 기반) ─────────────────────────────────────
NAVY = "#003366"          # 대제목 번호 박스 배경
NAVY_LINE = "#315F97"     # 대제목 제목 밑줄
TITLE_BG = "#DFEAF5"      # 제목 표 배경 (연하늘)

# ── 폰트 정의 ────────────────────────────────────────────────────────
REQUIRED_FONTS = [
    ("맑은 고딕",    "FCAT_GOTHIC",  "6", "4"),
    ("HY헤드라인M",  "FCAT_GOTHIC",  "6", "0"),
    ("휴먼명조",     "FCAT_MYUNGJO", "6", "0"),
]

# ── charPr 정의 (name, height_100ths, font_name, bold, color) ───────
CHAR_STYLES = [
    ("meta",         1300, "휴먼명조",     False, "#000000"),
    ("title",        2000, "HY헤드라인M",  False, "#000000"),
    ("sec_num",      1500, "맑은 고딕",    True,  "#FFFFFF"),
    ("sec_title",    1600, "HY헤드라인M",  False, "#000000"),
    ("h2",           1600, "HY헤드라인M",  False, "#000000"),
    ("body",         1500, "휴먼명조",     False, "#000000"),
    ("body_bold",    1500, "휴먼명조",     True,  "#000000"),
    ("note",         1200, "맑은 고딕",    False, "#000000"),
    ("tbl_hdr",      1200, "맑은 고딕",    True,  "#000000"),
    ("tbl_body",     1200, "맑은 고딕",    False, "#000000"),
    ("conclusion",   1500, "휴먼명조",     False, "#000000"),
]

# ── paraPr 정의 (name, halign, left_margin, indent, line_spacing_pct, prev, next) ─
# HWPUNIT: 7200 = 1 inch = 25.4mm.  2835 ≈ 10mm
# 간격 기준: 2800 ≈ 10mm,  1400 ≈ 5mm,  700 ≈ 2.5mm
PARA_STYLES = [
    #  name         halign     left  indent  lspct  prev  next
    ("meta",      "CENTER",     0,    0,    130,    0,  700),
    ("title",     "CENTER",     0,    0,    130,    0, 2000),  # 제목 아래 ~7mm 여백
    ("sec_num",   "CENTER",     0,    0,    160,    0,    0),
    ("sec_title", "JUSTIFY",    0,    0,    160,    0,    0),
    ("h2",        "JUSTIFY", 2800,    0,    160, 2400,  400),  # □ 중제목: 위 ~8mm, 아래 ~1.5mm
    ("body",      "JUSTIFY", 4200,    0,    160,  400,    0),  # ○ 본문: 위 ~1.5mm
    ("body_sub",  "JUSTIFY", 5600,    0,    160,  200,    0),  # - 하위: 위 ~0.7mm
    ("note",      "JUSTIFY", 4200,    0,    150, 1000,    0),  # ※ 주석: 위 ~3.5mm
    ("tbl",       "CENTER",     0,    0,    160,    0,    0),
    ("conclusion","JUSTIFY", 4200,    0,    160, 1200,    0),  # ⇒ 결론: 위 ~4mm
    ("spacer",    "JUSTIFY",    0,    0,    130,    0,    0),  # 빈 줄 (섹션 간 간격)
    ("l3_heading","JUSTIFY", 4200,    0,    160, 1400,  400),  # 가. 소제목: 위 ~5mm
    ("attach",    "JUSTIFY",    0,    0,    160, 2800,    0),  # 붙임: 위 ~10mm
]

# ── 섹션 헤더 표 마커 (패치에서 식별용) ──────────────────────────────
SEC_HDR_MARKER = "§SEC§"   # _build_base에서 표 대신 마커 삽입
TITLE_MARKER = "§TITLE§"


def _today():
    wd = ["월","화","수","목","금","토","일"][datetime.now().weekday()]
    return datetime.now().strftime(f"%Y. %m. %d.({wd})")


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════
def create_gov_hwpx(doc: dict) -> str:
    output_path = doc.get("output", "보고서.hwpx")

    with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as tmp:
        tmp_path = tmp.name
    _build_base(doc, tmp_path)

    with zipfile.ZipFile(tmp_path, 'r') as z:
        header_bytes = z.read("Contents/header.xml")
        section_bytes = z.read("Contents/section0.xml")

    new_header, style_map, bf_map = _patch_header(header_bytes)
    new_section = _patch_section(section_bytes, style_map, bf_map,
                                  doc_title=doc.get("title",""),
                                  doc=doc)

    _repack(tmp_path, output_path, new_header, new_section)
    os.unlink(tmp_path)

    print(f"✅ HWPX 생성 완료: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════════════════
# STEP 1: 기본 문서 뼈대
# ═══════════════════════════════════════════════════════════════════════
def _build_base(doc, path):
    hwpx = HwpxDocument.new()

    # 메타
    dt = doc.get("doc_type", "서면보고")
    date = doc.get("date", _today())
    dept = doc.get("dept", "")
    author = doc.get("author", "")
    meta = " | ".join([p for p in [dt, date, f"{dept} {author}".strip()] if p])
    hwpx.add_paragraph(meta)
    hwpx.add_paragraph("")

    # 제목 → 1×1 표로 생성 (패치에서 배경색/테두리 적용)
    title = doc.get("title", "보고서")
    tbl = hwpx.add_table(1, 1)
    tbl.set_cell_text(0, 0, title)
    hwpx.add_paragraph("")

    # 섹션
    cnt = [0, 0, 0]

    def render(sec, level):
        cnt[level-1] += 1
        for i in range(level, 3):
            cnt[i] = 0
        heading = sec.get("heading", "")

        if level == 1:
            num = NUM_L1[min(cnt[0]-1, len(NUM_L1)-1)]
            # 대제목 전 빈줄 (첫 섹션 제외)
            if cnt[0] > 1:
                hwpx.add_paragraph("")
            # 대제목 → 1×3 표로 생성 (패치에서 남색 박스 적용)
            tbl = hwpx.add_table(1, 3)
            tbl.set_cell_text(0, 0, num)
            tbl.set_cell_text(0, 1, "")
            tbl.set_cell_text(0, 2, heading)
        elif level == 2:
            hwpx.add_paragraph(f"{BULLET_H2} {heading}")
        else:
            num = NUM_L3[min(cnt[2]-1, len(NUM_L3)-1)]
            hwpx.add_paragraph(f"{num}. {heading}")

        # ── 계층 규칙 ──
        # Ⅰ(level1)에서는 직접 ○ 본문 금지 → 반드시 □(subsection) 먼저
        # □(level2)에서는 ○ 본문 → 하위(subsection) 순서
        # 가.(level3)에서는 - 본문 순서
        if level == 1:
            # level 1: subsections(□) 먼저 → 이후 paragraphs(혹시 있으면)
            for sub in sec.get("subsections", []):
                render(sub, level + 1)

            # level 1의 직접 paragraphs (보통 없어야 하지만 혹시 있으면)
            bullet = BULLET_L1
            for para in sec.get("paragraphs", []):
                hwpx.add_paragraph(f"{bullet} {para}")
        else:
            # level 2+: paragraphs 먼저 → subsections 나중
            bullet = BULLET_L1 if level == 2 else BULLET_L2
            for para in sec.get("paragraphs", []):
                hwpx.add_paragraph(f"{bullet} {para}")

            for sub in sec.get("subsections", []):
                render(sub, level + 1)

        # 주석
        for note in sec.get("notes", []):
            hwpx.add_paragraph(f"※ {note}")

        # 결론
        for conc in sec.get("conclusions", []):
            hwpx.add_paragraph(f"⇒ {conc}")

        # 표
        if "table" in sec:
            rows = sec["table"].get("rows", [])
            if rows:
                hwpx.add_paragraph("")
                col_count = max(len(r) for r in rows)
                tbl = hwpx.add_table(len(rows), col_count)
                for ri, row in enumerate(rows):
                    for ci in range(col_count):
                        txt = str(row[ci]) if ci < len(row) else ""
                        tbl.set_cell_text(ri, ci, txt)
                hwpx.add_paragraph("")

    for sec in doc.get("sections", []):
        render(sec, 1)

    # 붙임
    for i, att in enumerate(doc.get("attachments", []), 1):
        hwpx.add_paragraph(f"붙임{i}  {att}")

    # 담당자 표
    contacts = doc.get("contacts", [])
    if contacts:
        hwpx.add_paragraph("")
        rows = [["담당 부서", "담당자", "연락처"]]
        for c in contacts:
            rows.append([c.get("dept",""), c.get("name",""), c.get("tel","")])
        tbl = hwpx.add_table(len(rows), 3)
        for ri, row in enumerate(rows):
            for ci in range(3):
                tbl.set_cell_text(ri, ci, row[ci] if ci < len(row) else "")

    hwpx.save_to_path(path)


# ═══════════════════════════════════════════════════════════════════════
# STEP 2: header.xml 패치
# ═══════════════════════════════════════════════════════════════════════
def _patch_header(header_bytes):
    tree = etree.fromstring(header_bytes)
    style_map = {}
    bf_map = {}

    # ── 폰트 등록 ──
    font_id_map = {}
    for ff in tree.findall(f'.//{{{HH}}}fontface'):
        lang = ff.get('lang')
        cnt = int(ff.get('fontCnt', '2'))
        for font_name, ftype, weight, prop in REQUIRED_FONTS:
            exists = False
            for f in ff.findall(f'{{{HH}}}font'):
                if f.get('face') == font_name:
                    font_id_map.setdefault(font_name, {})[lang] = f.get('id')
                    exists = True
                    break
            if not exists:
                font = etree.SubElement(ff, f'{{{HH}}}font')
                font.set('id', str(cnt))
                font.set('face', font_name)
                font.set('type', 'TTF')
                font.set('isEmbedded', '0')
                ti = etree.SubElement(font, f'{{{HH}}}typeInfo')
                ti.set('familyType', ftype); ti.set('weight', weight)
                ti.set('proportion', prop)
                for a in ['contrast','strokeVariation','armStyle','letterform','midline','xHeight']:
                    ti.set(a, '0')
                font_id_map.setdefault(font_name, {})[lang] = str(cnt)
                cnt += 1
        ff.set('fontCnt', str(cnt))

    def _get_font_id(font_name):
        ids = font_id_map.get(font_name, {})
        return ids.get('HANGUL', ids.get(next(iter(ids), ''), '0'))

    # ── charPr 추가 ──
    cps = tree.find(f'.//{{{HH}}}charProperties')
    base_cp = cps.find(f'{{{HH}}}charPr[@id="0"]')
    existing = int(cps.get('itemCnt', '7'))

    for i, (name, height, font_name, bold, color) in enumerate(CHAR_STYLES):
        new_id = existing + i
        style_map[f'cp_{name}'] = str(new_id)
        cp = copy.deepcopy(base_cp)
        cp.set('id', str(new_id))
        cp.set('height', str(height))
        cp.set('textColor', color)
        fref = cp.find(f'{{{HH}}}fontRef')
        if fref is not None:
            fid = _get_font_id(font_name)
            for la in ['hangul','latin','hanja','japanese','other','symbol','user']:
                specific = font_id_map.get(font_name, {}).get(la.upper(), fid)
                fref.set(la, specific)
        existing_bold = cp.find(f'{{{HH}}}bold')
        if bold and existing_bold is None:
            etree.SubElement(cp, f'{{{HH}}}bold')
        elif not bold and existing_bold is not None:
            cp.remove(existing_bold)
        cps.append(cp)

    cps.set('itemCnt', str(existing + len(CHAR_STYLES)))

    # ── paraPr 추가 ──
    pps = tree.find(f'.//{{{HH}}}paraProperties')
    base_pp = pps.find(f'{{{HH}}}paraPr[@id="0"]')
    pp_cnt = int(pps.get('itemCnt', '0'))

    for name, halign, left_margin, indent, line_pct, prev, nxt in PARA_STYLES:
        new_pp_id = pp_cnt
        pp_cnt += 1
        pp = copy.deepcopy(base_pp)
        pp.set('id', str(new_pp_id))
        align_el = pp.find(f'{{{HH}}}align')
        if align_el is not None:
            align_el.set('horizontal', halign)
        # margin: 자식 요소(hc:left, hc:prev 등)의 value를 수정해야 함
        for margin in pp.iter(f'{{{HH}}}margin'):
            for child in margin:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag == 'left':
                    child.set('value', str(left_margin))
                elif tag == 'intent':  # HWPX는 indent가 아니라 intent
                    child.set('value', str(indent))
                elif tag == 'prev':
                    child.set('value', str(prev))
                elif tag == 'next':
                    child.set('value', str(nxt))
        for ls in pp.iter(f'{{{HH}}}lineSpacing'):
            ls.set('type', 'PERCENT')
            ls.set('value', str(line_pct))
        pps.append(pp)
        style_map[f'pp_{name}'] = str(new_pp_id)

    pps.set('itemCnt', str(pp_cnt))

    # ── borderFill 추가 ──
    bfs = tree.find(f'.//{{{HH}}}borderFills')
    bf_cnt = int(bfs.get('itemCnt', '3'))

    # 1) 제목 표 배경: 연하늘 #DFEAF5, 하단+우측 굵은선
    bf_cnt += 1
    bf_map['title_box'] = str(bf_cnt)
    bfs.append(_bf_title_box(bf_cnt))

    # 2) 대제목 번호 셀: 남색 #003366 배경
    bf_cnt += 1
    bf_map['sec_num_box'] = str(bf_cnt)
    bfs.append(_bf_sec_num_box(bf_cnt))

    # 3) 대제목 간격 셀: 투명, 테두리 없음
    bf_cnt += 1
    bf_map['sec_gap'] = str(bf_cnt)
    bfs.append(_bf_sec_gap(bf_cnt))

    # 4) 대제목 제목 셀: 하단 남색 밑줄
    bf_cnt += 1
    bf_map['sec_title_box'] = str(bf_cnt)
    bfs.append(_bf_sec_title_box(bf_cnt))

    # 5) 대제목 표 외곽: 테두리 없음
    bf_cnt += 1
    bf_map['sec_hdr_tbl'] = str(bf_cnt)
    bfs.append(_bf_no_border(bf_cnt))

    # 6) 일반 표 헤더
    bf_cnt += 1
    bf_map['tbl_hdr'] = str(bf_cnt)
    bfs.append(_bf_table_header(bf_cnt))

    # 7) 일반 표 본문
    bf_cnt += 1
    bf_map['tbl_body'] = str(bf_cnt)
    bfs.append(_bf_table_body(bf_cnt))

    bfs.set('itemCnt', str(bf_cnt))

    result = etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
    return result, style_map, bf_map


# ── borderFill 빌더들 ────────────────────────────────────────────────

def _bf_title_box(bf_id):
    """제목: 연하늘(#DFEAF5) 배경, 하단/우측 굵은선"""
    bf = _bf_base(bf_id)
    _add_border(bf, 'leftBorder',   'SOLID', '0.12 mm', '#000000')
    _add_border(bf, 'rightBorder',  'SOLID', '0.5 mm',  '#000000')
    _add_border(bf, 'topBorder',    'SOLID', '0.12 mm', '#000000')
    _add_border(bf, 'bottomBorder', 'SOLID', '0.5 mm',  '#000000')
    _add_fill(bf, TITLE_BG)
    return bf

def _bf_sec_num_box(bf_id):
    """대제목 번호 셀: 남색(#003366) 배경, 사방 남색 얇은선"""
    bf = _bf_base(bf_id)
    for side in ['leftBorder','rightBorder','topBorder','bottomBorder']:
        _add_border(bf, side, 'SOLID', '0.1 mm', NAVY)
    _add_fill(bf, NAVY)
    return bf

def _bf_sec_gap(bf_id):
    """대제목 간격 셀: 투명, 테두리 없음"""
    bf = _bf_base(bf_id)
    for side in ['leftBorder','rightBorder','topBorder','bottomBorder']:
        _add_border(bf, side, 'NONE', '0.12 mm', '#000000')
    return bf

def _bf_sec_title_box(bf_id):
    """대제목 제목 셀: 하단 남색 밑줄, 나머지 없음"""
    bf = _bf_base(bf_id)
    _add_border(bf, 'leftBorder',   'NONE',  '0.25 mm', NAVY_LINE)
    _add_border(bf, 'rightBorder',  'NONE',  '0.25 mm', NAVY_LINE)
    _add_border(bf, 'topBorder',    'NONE',  '0.25 mm', NAVY_LINE)
    _add_border(bf, 'bottomBorder', 'SOLID', '0.5 mm',  NAVY_LINE)
    return bf

def _bf_no_border(bf_id):
    """테두리 없는 표 외곽"""
    bf = _bf_base(bf_id)
    for side in ['leftBorder','rightBorder','topBorder','bottomBorder']:
        _add_border(bf, side, 'NONE', '0.12 mm', '#000000')
    return bf

def _bf_table_header(bf_id):
    """일반 표 헤더: 사방 실선, 상하 굵은선"""
    bf = _bf_base(bf_id)
    _add_border(bf, 'leftBorder',   'SOLID', '0.12 mm', '#000000')
    _add_border(bf, 'rightBorder',  'SOLID', '0.12 mm', '#000000')
    _add_border(bf, 'topBorder',    'SOLID', '0.4 mm',  '#000000')
    _add_border(bf, 'bottomBorder', 'SOLID', '0.4 mm',  '#000000')
    return bf

def _bf_table_body(bf_id):
    """일반 표 본문: 사방 얇은 실선"""
    bf = _bf_base(bf_id)
    for side in ['leftBorder','rightBorder','topBorder','bottomBorder']:
        _add_border(bf, side, 'SOLID', '0.12 mm', '#000000')
    return bf

def _bf_base(bf_id):
    bf = etree.Element(f'{{{HH}}}borderFill')
    bf.set('id', str(bf_id)); bf.set('threeD','0'); bf.set('shadow','0')
    bf.set('centerLine','NONE'); bf.set('breakCellSeparateLine','0')
    for t in ['slash','backSlash']:
        el = etree.SubElement(bf, f'{{{HH}}}{t}')
        el.set('type','NONE'); el.set('Crooked','0'); el.set('isCounter','0')
    return bf

def _add_border(bf, side, btype, width, color):
    el = etree.SubElement(bf, f'{{{HH}}}{side}')
    el.set('type', btype); el.set('width', width); el.set('color', color)

def _add_fill(bf, face_color):
    fb = etree.SubElement(bf, f'{{{HC}}}fillBrush')
    wb = etree.SubElement(fb, f'{{{HC}}}winBrush')
    wb.set('faceColor', face_color)
    wb.set('hatchColor', '#000000')
    wb.set('alpha', '0')


# ═══════════════════════════════════════════════════════════════════════
# STEP 3: section0.xml 패치
# ═══════════════════════════════════════════════════════════════════════
def _patch_section(section_bytes, style_map, bf_map, doc_title="", doc=None):
    tree = etree.fromstring(section_bytes)

    sec_nums_set = set(NUM_L1)
    sec_headings = []
    if doc:
        for sec in doc.get("sections", []):
            sec_headings.append(sec.get("heading", ""))

    # ── 표 서식 적용 ──
    tbl_index = 0
    sec_hdr_count = 0  # 대제목 표 카운터
    num_sections = len(doc.get("sections", [])) if doc else 0

    for tbl in tree.findall(f'.//{{{HP}}}tbl'):
        rows = int(tbl.get('rowCnt', '0'))
        cols = int(tbl.get('colCnt', '0'))

        # 첫 번째 셀 텍스트 확인
        first_text = ""
        for t_elem in tbl.iter(f'{{{HP}}}t'):
            if t_elem.text and t_elem.text.strip():
                first_text = t_elem.text.strip()
                break

        if rows == 1 and cols == 1 and first_text == doc_title.strip():
            # ── 제목 표 (1×1) ──
            _apply_title_table(tbl, style_map, bf_map)

        elif rows == 1 and cols == 3 and first_text.rstrip('.') in sec_nums_set:
            # ── 대제목 표 (1×3) ──
            _apply_sec_header_table(tbl, style_map, bf_map)
            sec_hdr_count += 1

        else:
            # ── 일반 데이터 표 ──
            _apply_data_table(tbl, style_map, bf_map)

    # ── 문단 스타일 적용 ──
    prev_was_sec_num = False

    for p in tree.findall(f'{{{HP}}}p'):
        runs = p.findall(f'{{{HP}}}run')
        text = ""
        for r in runs:
            t = r.find(f'{{{HP}}}t')
            if t is not None and t.text:
                text = t.text.strip()
                break

        char_id, para_id = None, None

        if not text:
            # 빈 문단 → spacer 스타일 적용
            para_id = style_map.get('pp_spacer')
            if para_id:
                p.set('paraPrIDRef', para_id)
            continue

        is_sec_num = text.rstrip('.') in sec_nums_set

        if _is_meta(text):
            char_id = style_map.get('cp_meta')
            para_id = style_map.get('pp_meta')
        elif text.startswith(BULLET_H2):
            char_id = style_map.get('cp_h2')
            para_id = style_map.get('pp_h2')
        elif text.startswith("⇒"):
            char_id = style_map.get('cp_conclusion')
            para_id = style_map.get('pp_conclusion')
        elif text.startswith("※"):
            char_id = style_map.get('cp_note')
            para_id = style_map.get('pp_note')
        elif text.startswith("붙임"):
            char_id = style_map.get('cp_sec_title')
            para_id = style_map.get('pp_attach')
        elif text.startswith(BULLET_L1):
            char_id = style_map.get('cp_body')
            para_id = style_map.get('pp_body')
        elif text.startswith(BULLET_L2 + " "):
            char_id = style_map.get('cp_body')
            para_id = style_map.get('pp_body_sub')
        elif any(text.startswith(f"{n}.") for n in NUM_L3):
            char_id = style_map.get('cp_h2')
            para_id = style_map.get('pp_l3_heading')
        elif not text:
            # 빈 문단 → 좁은 간격 스페이서
            para_id = style_map.get('pp_spacer')
        else:
            char_id = style_map.get('cp_body')
            para_id = style_map.get('pp_body')

        if char_id:
            for r in runs:
                if r.find(f'{{{HP}}}secPr') is not None:
                    continue
                r.set('charPrIDRef', char_id)
        if para_id:
            p.set('paraPrIDRef', para_id)

    return etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)


def _apply_title_table(tbl, style_map, bf_map):
    """제목 1×1 표: 연하늘 배경, 20pt HY헤드라인M"""
    # 표 외곽 borderFill을 제목 스타일로
    tbl.set('borderFillIDRef', bf_map.get('title_box', '1'))

    sz = tbl.find(f'{{{HP}}}sz')
    if sz is not None:
        sz.set('width', str(DOC_TEXT_WIDTH))

    for tc in tbl.iter(f'{{{HP}}}tc'):
        tc.set('borderFillIDRef', bf_map.get('title_box', '1'))
        csz = tc.find(f'{{{HP}}}cellSz')
        if csz is not None:
            csz.set('width', str(DOC_TEXT_WIDTH))

        # 셀 내 텍스트 스타일
        for run in tc.iter(f'{{{HP}}}run'):
            run.set('charPrIDRef', style_map.get('cp_title', '0'))
        for sub_p in tc.iter(f'{{{HP}}}p'):
            pp_id = style_map.get('pp_title', None)
            if pp_id:
                sub_p.set('paraPrIDRef', pp_id)


def _apply_sec_header_table(tbl, style_map, bf_map):
    """대제목 1×3 표: [남색박스 Ⅰ] [간격] [밑줄 제목]"""
    # 표 외곽: 테두리 없음
    tbl.set('borderFillIDRef', bf_map.get('sec_hdr_tbl', '1'))

    # 표 전체 폭 설정
    sz = tbl.find(f'{{{HP}}}sz')
    if sz is not None:
        sz.set('width', str(DOC_TEXT_WIDTH))

    trs = tbl.findall(f'{{{HP}}}tr')
    if not trs:
        return

    tcs = trs[0].findall(f'{{{HP}}}tc')
    if len(tcs) < 3:
        return

    # 셀 0: 남색 번호 박스
    tc0 = tcs[0]
    tc0.set('borderFillIDRef', bf_map.get('sec_num_box', '1'))
    csz0 = tc0.find(f'{{{HP}}}cellSz')
    if csz0 is not None:
        csz0.set('width', '2573')
        csz0.set('height', '2466')
    for run in tc0.iter(f'{{{HP}}}run'):
        run.set('charPrIDRef', style_map.get('cp_sec_num', '0'))
    for sub_p in tc0.iter(f'{{{HP}}}p'):
        sub_p.set('paraPrIDRef', style_map.get('pp_sec_num', '0'))

    # 셀 1: 간격 (투명)
    tc1 = tcs[1]
    tc1.set('borderFillIDRef', bf_map.get('sec_gap', '1'))
    csz1 = tc1.find(f'{{{HP}}}cellSz')
    if csz1 is not None:
        csz1.set('width', '566')
        csz1.set('height', '2466')

    # 셀 2: 제목 (하단 남색 밑줄)
    tc2 = tcs[2]
    tc2.set('borderFillIDRef', bf_map.get('sec_title_box', '1'))
    csz2 = tc2.find(f'{{{HP}}}cellSz')
    if csz2 is not None:
        remaining_w = DOC_TEXT_WIDTH - 2573 - 566  # 39381
        csz2.set('width', str(remaining_w))
        csz2.set('height', '2466')
    for run in tc2.iter(f'{{{HP}}}run'):
        run.set('charPrIDRef', style_map.get('cp_sec_title', '0'))
    for sub_p in tc2.iter(f'{{{HP}}}p'):
        sub_p.set('paraPrIDRef', style_map.get('pp_sec_title', '0'))

    # subList vertAlign → CENTER
    for sl in tbl.iter(f'{{{HP}}}subList'):
        sl.set('vertAlign', 'CENTER')


def _apply_data_table(tbl, style_map, bf_map):
    """일반 데이터 표: 헤더 굵은선 + bold, 본문 얇은선"""
    col_cnt = int(tbl.get('colCnt', '3'))
    col_w = DOC_TEXT_WIDTH // col_cnt

    sz = tbl.find(f'{{{HP}}}sz')
    if sz is not None:
        sz.set('width', str(DOC_TEXT_WIDTH))

    for ri, tr in enumerate(tbl.findall(f'{{{HP}}}tr')):
        for ci, tc in enumerate(tr.findall(f'{{{HP}}}tc')):
            csz = tc.find(f'{{{HP}}}cellSz')
            if csz is not None:
                csz.set('width', str(col_w))

            if ri == 0:
                tc.set('borderFillIDRef', bf_map.get('tbl_hdr', '3'))
                tc.set('header', '1')
                _set_cell_style(tc, style_map.get('cp_tbl_hdr', '0'))
            else:
                tc.set('borderFillIDRef', bf_map.get('tbl_body', '3'))
                _set_cell_style(tc, style_map.get('cp_tbl_body', '0'))

            for sub_p in tc.iter(f'{{{HP}}}p'):
                pp_id = style_map.get('pp_tbl', None)
                if pp_id:
                    sub_p.set('paraPrIDRef', pp_id)


# ── 헬퍼 ─────────────────────────────────────────────────────────────
_sec_num_set = set(NUM_L1)

def _is_meta(text):
    return ("|" in text and ("서면보고" in text or "기안" in text or
            "대면보고" in text or "보고" in text))

def _set_cell_style(tc, char_id):
    for run in tc.iter(f'{{{HP}}}run'):
        run.set('charPrIDRef', str(char_id))


# ═══════════════════════════════════════════════════════════════════════
# STEP 4: ZIP 재조립
# ═══════════════════════════════════════════════════════════════════════
def _repack(src, dst, new_header, new_section):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(src, 'r') as z:
            z.extractall(tmpdir)
        with open(os.path.join(tmpdir, "Contents", "header.xml"), 'wb') as f:
            f.write(new_header)
        with open(os.path.join(tmpdir, "Contents", "section0.xml"), 'wb') as f:
            f.write(new_section)
        with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
            mt = os.path.join(tmpdir, "mimetype")
            if os.path.exists(mt):
                zout.write(mt, "mimetype", compress_type=zipfile.ZIP_STORED)
            for root, _, files in os.walk(tmpdir):
                for fn in files:
                    full = os.path.join(root, fn)
                    arc = os.path.relpath(full, tmpdir)
                    if arc == "mimetype":
                        continue
                    zout.write(full, arc)


# ═══════════════════════════════════════════════════════════════════════
# CLI (cdsa-hwpsx 래퍼 전용 진입점)
# ═══════════════════════════════════════════════════════════════════════
def _run_from_json_arg():
    """
    사용법:
      python3 generate_hwpx.py --json <doc.json 파일 경로>
      python3 generate_hwpx.py --demo
    두 옵션이 없으면 기존 데모를 그대로 실행 (하위 호환).
    """
    import json
    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        json_path = sys.argv[idx + 1]
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        create_gov_hwpx(doc)
        return True
    return False


if __name__ == "__main__":
    if _run_from_json_arg():
        sys.exit(0)

    demo = {
        "title": "AI시대 행정문서 작성 가이드라인(안) 보고",
        "doc_type": "서면보고",
        "date": _today(),
        "dept": "혁신행정담당관",
        "author": "박은희 사무관",
        "sections": [
            {
                "heading": "추진 배경",
                "subsections": [
                    {
                        "heading": "추진 필요성",
                        "paragraphs": [
                            "정부는 사람과 AI 모두 쉽게 읽고 작성할 수 있는 표준화된 문서 작성 가이드라인을 수립할 필요가 있음.",
                        ],
                    },
                    {
                        "heading": "현황 분석",
                        "paragraphs": ["현행 문서 형식의 한계를 분석함."],
                    },
                ],
            },
            {
                "heading": "주요 추진 내용",
                "subsections": [
                    {
                        "heading": "가이드라인 배포 및 시범 실시",
                        "paragraphs": [
                            "행정안전부는 AI 친화적 보고서 작성을 위해 가이드라인을 전 부서에 배포하고 시범 실시함.",
                        ],
                        "table": {"rows": [["구분","기존 방식","개선 방식"],["문서 형식","개조식","서술식"],["표 작성","셀 병합 허용","셀 병합 금지"]]},
                    },
                ],
                "conclusions": ["보안 체계와 AI 혁신은 동시 추구 가치이며, 안전한 혁신이 가능하도록 제도 마련 필요"],
            },
        ],
        "contacts": [{"dept": "혁신행정담당관", "name": "박은희 사무관", "tel": "044-205-1473"}],
        "output": "보고서_데모.hwpx",
    }
    create_gov_hwpx(demo)
