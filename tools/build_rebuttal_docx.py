#!/usr/bin/env python3
"""Build the illustrated bilingual rebuttal DOCX.

Reads the final English/Chinese rebuttals and the generated figures, and writes
rebuttal_illustrated.docx in the workspace root.

Run with the bundled python-docx runtime:
  /Users/cmy/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3 \
    tools/build_rebuttal_docx.py
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "tmp" / "doc_figures"
OUT = ROOT / "rebuttal_illustrated.docx"

NAVY = RGBColor(0x1A, 0x36, 0x5D)
BLUE = RGBColor(0x2B, 0x6C, 0xB0)
GRAY = RGBColor(0x4A, 0x55, 0x68)
LIGHT = RGBColor(0x71, 0x80, 0x96)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ORANGE = RGBColor(0xC0, 0x56, 0x21)

BODY_PT = 10
ZH_BODY_PT = 9.5
CAPTION_PT = 8


def set_run_font(run, size=BODY_PT, bold=None, italic=None, color=None, mono=False, zh=False):
    run.font.name = "Consolas" if mono else "Arial"
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), "Consolas" if mono else "Arial")
    rfonts.set(qn("w:hAnsi"), "Consolas" if mono else "Arial")
    rfonts.set(qn("w:eastAsia"), "PingFang SC" if zh else "Arial")


def add_rich(paragraph, text, size=BODY_PT, color=None, zh=False, bold_color=None):
    """Render **bold** and `code` spans without dropping the rest of the text."""
    for part in re.split(r"(\*\*.*?\*\*|`[^`]*`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            run = paragraph.add_run(part[2:-2])
            set_run_font(run, size=size, bold=True, color=bold_color or color, zh=zh)
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            set_run_font(run, size=size - 0.5, mono=True, color=RGBColor(0x2D, 0x37, 0x48), zh=zh)
        else:
            run = paragraph.add_run(part)
            set_run_font(run, size=size, color=color, zh=zh)


def shade(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def cell_margins(cell, top=90, bottom=90, left=120, right=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for side, value in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tc_pr.append(mar)


def table_borders(table, color="CBD5E0", size=4, inside=True):
    tbl = table._tbl
    borders = OxmlElement("w:tblBorders")
    edges = ["top", "left", "bottom", "right"] + (["insideH", "insideV"] if inside else [])
    for edge in edges:
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl.tblPr.append(borders)


def no_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def para_border_bottom(paragraph, color="CBD5E0", size=8):
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "6")
    bottom.set(qn("w:color"), color)
    borders.append(bottom)
    p_pr.append(borders)


def add_page_number(paragraph):
    run = paragraph.add_run()
    set_run_font(run, size=8, color=LIGHT)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


def heading(doc, text, level=1, zh=False):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(text)
    set_run_font(run, size=15 if level == 1 else 11.5, bold=True, color=NAVY if level == 1 else BLUE, zh=zh)
    return paragraph


def body(doc, text, zh=False, space_after=5, italic=False, size=None):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.line_spacing = 1.25 if zh else 1.15
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_rich(paragraph, text, size=size or (ZH_BODY_PT if zh else BODY_PT), zh=zh)
    if italic:
        for run in paragraph.runs:
            run.italic = True
    return paragraph


def caption(doc, text, zh=False):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(10)
    run = paragraph.add_run(text)
    set_run_font(run, size=CAPTION_PT, italic=True, color=LIGHT, zh=zh)


def figure(doc, name, width_cm, cap, zh=False):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(FIG / f"{name}.png"), width=Cm(width_cm))
    caption(doc, cap, zh=zh)


def box(doc, title, paragraphs, fill, border, title_color=NAVY, zh=False, italic=False):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Cm(16.2)
    cell = table.cell(0, 0)
    cell.width = Cm(16.2)
    shade(cell, fill)
    cell_margins(cell, top=120, bottom=120, left=180, right=180)
    table_borders(table, color=border, size=10, inside=False)
    no_split(table.rows[0])
    if title:
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(4)
        run = paragraph.add_run(title)
        set_run_font(run, size=10, bold=True, color=title_color, zh=zh)
        first = False
    else:
        first = True
    for text in paragraphs:
        paragraph = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.paragraph_format.line_spacing = 1.2
        add_rich(paragraph, text, size=9 if zh else 9.2, zh=zh)
        if italic:
            for run in paragraph.runs:
                run.italic = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def t1_table(doc, zh=False):
    header = ["", "PF", "B2", "B1"]
    rows = [
        ["有效题（480 槽位）" if zh else "valid items (of 480 slots)", "366 (76.3%)", "352 (73.3%)", "134 (27.9%)"],
        ["有效且 >=3 步" if zh else "valid, >=3 dependent steps", "301 (62.7%)", "162 (33.8%)", "28 (5.8%)"],
        ["推理深度均值 (0-4)" if zh else "reasoning depth, mean (0-4)", "2.94", "2.34", "1.93"],
        ["题面长度中位（字符）" if zh else "median length (chars)", "692", "321", "297"],
        ["near-dup @0.8", "3.0%", "24.9%", "6.2%"],
        ["每有效题 token（20/单位）" if zh else "tokens / valid item (20/u)", "12,267", "527", "4,571"],
    ]
    table = doc.add_table(rows=1 + len(rows), cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [Cm(6.2), Cm(3.4), Cm(3.4), Cm(3.4)]
    for row in table.rows:
        no_split(row)
    header_tr = table.rows[0]._tr
    header_tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for index, text in enumerate(header):
        cell = table.rows[0].cells[index]
        cell.width = widths[index]
        shade(cell, "2B6CB0")
        cell_margins(cell, top=60, bottom=60, left=90, right=90)
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if index else WD_ALIGN_PARAGRAPH.LEFT
        run = paragraph.add_run(text)
        set_run_font(run, size=8.5, bold=True, color=WHITE, zh=zh)
    for r, values in enumerate(rows, start=1):
        for c, text in enumerate(values):
            cell = table.rows[r].cells[c]
            cell.width = widths[c]
            cell_margins(cell, top=28, bottom=28, left=90, right=90)
            if r % 2 == 0:
                shade(cell, "F7FAFC")
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if c else WD_ALIGN_PARAGRAPH.LEFT
            run = paragraph.add_run(text)
            set_run_font(run, size=8.5, zh=zh)
    table_borders(table, color="CBD5E0", size=4, inside=True)


def parse(path: Path):
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text)
    quote, paragraphs = [], []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("# ") or block.startswith("## "):
            continue
        if block.startswith(">"):
            for line in block.split("\n"):
                line = line.strip()
                if line.startswith(">"):
                    line = line[1:].strip()
                bare = line.strip("* ").strip()
                if bare.lower() in ("reviewer comment", "审稿人意见"):
                    continue
                if line.lower().startswith("中文要点"):
                    continue
                if line:
                    quote.append(line)
            continue
        if block.startswith("```") or block.startswith("**Table T1") or block.startswith("**表 T1"):
            continue
        if block.startswith("*Percentages") or block.startswith("*百分比"):
            paragraphs.append(("note", block.strip("*")))
            continue
        paragraphs.append(("p", block))
    return quote, paragraphs


def render_part(doc, paragraphs, zh=False):
    first = True
    for kind, text in paragraphs:
        if kind == "note":
            caption(doc, text, zh=zh)
            continue
        if first and not zh and text.startswith("**Design.**"):
            pass
        first = False
        if text.startswith("**Design.**") or text.startswith("**设置"):
            body(doc, text, zh=zh)
            caption(doc, "Table 1. What each pipeline yields per requested slot "
                         "(480 slots per condition; token row at 20 instances/unit)." if not zh else
                         "表 1. 三条流水线每个请求槽位的产出（每条件 480 槽位；token 行为 20 实例/单位）。",
                   zh=zh)
            t1_table(doc, zh=zh)

        elif text.startswith("**Against B2**") or text.startswith("**对 B2**"):
            body(doc, text, zh=zh)
            figure(doc, "fig1_validity", 12.8,
                   "Figure 1. Blind validity by pipeline (480 items each; bars are seed-macro means, "
                   "whiskers are 95% bootstrap intervals over seeds)." if not zh else
                   "图 1. 三条流水线的盲评有效率（每组 480 题；柱为 seed 宏平均，须为 2,000 次 seed bootstrap 的 95% 区间）。",
                   zh=zh)
        elif text.startswith("Because PF items") or text.startswith("PF 的题面"):
            body(doc, text, zh=zh)
            figure(doc, "fig3_length", 16.0,
                   "Figure 2. Depth among valid items and >=3-step yield per requested slot, by pooled "
                   "problem-length quintile. PF is higher on yield in every quintile; B2 matches PF on depth "
                   "only in Q5, where B2 has 16 valid items." if not zh else
                   "图 2. 按题面长度五分位分层的 depth（仅有效题）与每槽位 >=3 步产出率。PF 在每个分位的产出率都更高；"
                   "B2 只在 Q5 的 depth 追平，而 Q5 的 B2 只有 16 道有效题。",
                   zh=zh)
        elif text.startswith("**Cost.**") or text.startswith("**成本"):
            body(doc, text, zh=zh)
            figure(doc, "fig4_cost", 15.0,
                   "Figure 3. Generation tokens per valid item at two amortisation scales. PF/B2 is ~25x "
                   "at either scale; B2's 50 at 200 instances/unit is the design-scale number." if not zh else
                   "图 3. 两个摊销尺度下每道有效题的生成 token。PF/B2 在两个尺度上都是 ~25 倍；"
                   "B2 在 200 实例/单位下是 50，这是设计尺度的数字。",
                   zh=zh)
        elif text.startswith("**Judge reliability.**") or text.startswith("**评审可靠性"):
            body(doc, text, zh=zh)
            figure(doc, "fig2_judges", 15.0,
                   "Figure 4. Validity under two judge families on the 560-item overlap. The bar spans strict "
                   "(both valid) to liberal (either valid); points are the two families. B1 stays far below "
                   "PF/B2 under both." if not zh else
                   "图 4. 560 题重叠样本上两个评审家族的有效率。横条从 strict（两家都判 valid）到 liberal"
                   "（任一家判 valid）；点是两个家族。B1 在两个家族下都远低于 PF/B2。",
                   zh=zh)
        elif text.startswith("**What the 23.1%") or text.startswith("**23.1%"):
            cleaned = re.sub(r"^\*\*.*?\*\*\s*", "", text, count=1)
            box(doc, "Two real items behind the 23.1%" if not zh else "23.1% 背后的两个真实例子",
                [cleaned], "FFFAF0", "DD6B20", title_color=ORANGE, zh=zh)
        else:
            body(doc, text, zh=zh)


def main():
    en_quote, en_paras = parse(ROOT / "rebuttal_response.md")
    zh_quote, zh_paras = parse(ROOT / "rebuttal_response_zh.md")

    doc = Document()
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.header_distance = Cm(0.9)
    section.footer_distance = Cm(0.8)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(BODY_PT)
    normal_rpr = normal.element.get_or_add_rPr()
    normal_rfonts = normal_rpr.find(qn("w:rFonts"))
    if normal_rfonts is None:
        normal_rfonts = OxmlElement("w:rFonts")
        normal_rpr.append(normal_rfonts)
    normal_rfonts.set(qn("w:ascii"), "Arial")
    normal_rfonts.set(qn("w:hAnsi"), "Arial")
    normal_rfonts.set(qn("w:eastAsia"), "PingFang SC")

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("PuzzleForge  ·  Response to Reviewer Comment 4")
    set_run_font(run, size=8, color=LIGHT)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("Page ")
    set_run_font(run, size=8, color=LIGHT)
    add_page_number(footer)

    title = doc.add_paragraph()
    title.paragraph_format.space_before = Pt(6)
    title.paragraph_format.space_after = Pt(2)
    run = title.add_run("PuzzleForge: Response to Reviewer Comment 4")
    set_run_font(run, size=18, bold=True, color=NAVY)

    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(12)
    run = subtitle.add_run("Illustrated rebuttal  ·  97 seeds / 1,440 blind items  ·  29 October 2026")
    set_run_font(run, size=9.5, color=LIGHT)
    para_border_bottom(subtitle)

    box(doc, "At a glance",
        ["B1 (direct): 27.9% valid; PF is +48.4 pp.",
         "B2 (one-pass generator): 73.3% valid, statistically tied with PF (76.3%).",
         "PF yields 1.86x more valid >=3-step items per slot (62.7% vs 33.8%).",
         "Two judge families agree on 83.4% of verdicts; the B1 gap holds and the PF-B2 tie holds."],
        "EBF8FF", "90CDF4")

    label = doc.add_paragraph()
    label.paragraph_format.space_before = Pt(4)
    label.paragraph_format.space_after = Pt(3)
    run = label.add_run("REVIEWER COMMENT")
    set_run_font(run, size=8, bold=True, color=LIGHT)
    box(doc, "", en_quote, "F7FAFC", "CBD5E0", italic=True)

    heading(doc, "Response", 1)
    render_part(doc, en_paras, zh=False)

    doc.add_page_break()
    heading(doc, "中文翻译", 1, zh=True)
    render_part(doc, zh_paras, zh=True)

    doc.core_properties.title = "PuzzleForge: Response to Reviewer Comment 4"
    doc.core_properties.subject = "Illustrated rebuttal"
    doc.core_properties.author = "PuzzleForge authors"
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
