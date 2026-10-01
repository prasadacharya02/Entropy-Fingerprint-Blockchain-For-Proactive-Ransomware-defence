#!/usr/bin/env python3
"""Build the ENTROPY project report as a Word document.

    python report/build_report.py

The script renders ``report/report_content.py`` into
``report/ENTROPY_Project_Report.docx`` using a compact technical-report
style (A4, Calibri 11 pt body, numbered headings, captioned figures and
tables, page numbers in the footer).

Before writing the document it estimates the pagination of every block so
that the table of contents carries page numbers and so that the report
length can be checked against the twenty-page target.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_content as content  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "ENTROPY_Project_Report.docx"

NAVY = RGBColor(0x16, 0x32, 0x4F)
TEAL = RGBColor(0x2E, 0x86, 0xAB)
GREY = RGBColor(0x4A, 0x55, 0x68)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# ── Layout constants used by the estimator ────────────────────
PAGE_H = 11.69          # A4 height, inches
MARGIN = 0.8
USABLE_H = PAGE_H - 2 * MARGIN          # 9.99 in
TEXT_W = 8.27 - 2 * MARGIN              # 6.57 in

LINE_H = 0.156          # 10 pt at 1.08 spacing
CHARS_PER_LINE = 100    # conservative for Calibri 10 pt in 6.67 in
TABLE_LINE_H = 0.128    # 8.5 pt table text
TABLE_PAD = 0.05
CODE_LINE_H = 0.132     # 8 pt monospace
HEAD_H = {"h1": 0.55, "h2": 0.38, "h3": 0.30}


def _lines(text: str, chars_per_line: int = CHARS_PER_LINE) -> int:
    """Estimated wrapped line count of a paragraph."""
    if not text:
        return 1
    return max(1, math.ceil(len(text) / chars_per_line))


def block_height(kind: str, payload) -> float:
    """Estimated height of one content block, in inches."""
    if kind in HEAD_H:
        return HEAD_H[kind]
    if kind == "p":
        return _lines(payload) * LINE_H + 0.09
    if kind in ("bullets", "numbers"):
        return sum(_lines(t, CHARS_PER_LINE - 4) * LINE_H + 0.045
                   for t in payload)
    if kind == "refs":
        return sum(_lines(t, CHARS_PER_LINE - 8) * LINE_H + 0.05
                   for t in payload)
    if kind == "code":
        return len(payload.splitlines()) * CODE_LINE_H + 0.16
    if kind == "figure":
        aspect = payload.get("aspect", 0.45)
        caption_lines = _lines(payload["caption"], 108)
        return payload["width_in"] * aspect + caption_lines * 0.155 + 0.20
    if kind == "table":
        header_lines = max(_lines(c, max(4, int(w * 15)))
                           for c, w in zip(payload["header"], payload["widths"]))
        height = header_lines * TABLE_LINE_H + TABLE_PAD
        for row in payload["rows"]:
            row_lines = max(
                _lines(cell, max(4, int(w * 15)))
                for cell, w in zip(row, payload["widths"])
            )
            height += row_lines * TABLE_LINE_H + TABLE_PAD
        caption_lines = _lines(payload["caption"], 108)
        return height + caption_lines * 0.155 + 0.20
    if kind == "pagebreak":
        return 0.0
    if kind == "toc":
        return 0.0
    return 0.0


def estimate(blocks, start_page: int = 1):
    """Walk the blocks and return (page_map, total_pages, page_of_block)."""
    page = start_page
    y = 0.0
    page_of_block = []
    chapter_pages = {}
    for index, (kind, payload) in enumerate(blocks):
        height = block_height(kind, payload)
        if kind == "h1":
            if index > 0 and not str(payload).startswith(NO_BREAK_H1):
                page += 1
                y = 0.0
            page_of_block.append(page)
            chapter_pages.setdefault(payload, page)
            y += height
            continue
        if kind == "pagebreak":
            page += 1
            y = 0.0
            page_of_block.append(page)
            continue
        if y + height > USABLE_H:
            page += 1
            y = 0.0
        page_of_block.append(page)
        y += height
    return chapter_pages, page, page_of_block


# ── python-docx helpers ───────────────────────────────────────
def set_cell_shading(cell, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
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


def style_run(run, *, size=11, bold=False, italic=False, color=None,
              font="Calibri") -> None:
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), font)


def configure_styles(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    pf = normal.paragraph_format
    pf.space_after = Pt(5)
    pf.space_before = Pt(0)
    pf.line_spacing = 1.08
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, colour, before, after in (
        ("Heading 1", 15, NAVY, 0, 8),
        ("Heading 2", 12, TEAL, 10, 5),
        ("Heading 3", 11, NAVY, 8, 3),
    ):
        style = document.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = colour
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.line_spacing = 1.0
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for name in ("List Bullet", "List Number"):
        style = document.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(10)
        style.paragraph_format.space_after = Pt(2)
        style.paragraph_format.line_spacing = 1.05
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name in ("Caption",):
        style = document.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(8)
        style.font.italic = True
        style.font.color.rgb = GREY


def add_footer(section, title: str) -> None:
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.text = ""
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        Inches(TEXT_W), WD_TAB_ALIGNMENT.RIGHT
    )
    run = paragraph.add_run(f"{title}\t")
    style_run(run, size=8.5, color=GREY)
    prefix = paragraph.add_run("Page ")
    style_run(prefix, size=8.5, color=GREY)
    add_page_field(paragraph)
    for run in paragraph.runs:
        style_run(run, size=8.5, color=GREY)


# ── Block renderers ───────────────────────────────────────────
def render_title_page(document: Document, estimated_pages: int) -> None:
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(48)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(6)
    for line_no, line in enumerate(content.TITLE.split("\n")):
        run = title.add_run(line)
        style_run(run, size=22, bold=True, color=NAVY)
        if line_no == 0:
            title.add_run().add_break()

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(30)
    run = subtitle.add_run("ENTROPY — Ransomware Shield")
    style_run(run, size=15, bold=False, color=TEAL)

    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_after = Pt(36)
    run = note.add_run(
        "A working purple-team laboratory for entropy-based ransomware "
        "detection,\nverified containment, hash-verified recovery and auditable response"
    )
    style_run(run, size=11, italic=True, color=GREY)

    fields = [
        ("Project title", "Entropy Fingerprint Blockchain for Proactive Ransomware Defence"),
        ("Report type", "Technical project report"),
        ("Prepared by", "[Student / team names]"),
        ("Roll numbers", "[Roll numbers]"),
        ("Department", "[Department]"),
        ("Institution", "[College / university name]"),
        ("Internal guide", "[Guide name and designation]"),
        ("Academic year", "[20XX–20XX]"),
        ("Date", "[Date of submission]"),
    ]
    table = document.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for label, value in fields:
        row = table.add_row().cells
        row[0].width = Inches(1.8)
        row[1].width = Inches(3.6)
        p0 = row[0].paragraphs[0]
        run = p0.add_run(label)
        style_run(run, size=10, bold=True, color=NAVY)
        p1 = row[1].paragraphs[0]
        run = p1.add_run(value)
        style_run(run, size=10, color=GREY)

    document.add_paragraph()
    footer_note = document.add_paragraph()
    footer_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_note.add_run(
        f"Estimated length: {estimated_pages} pages  ·  "
        f"{len([b for b in content.blocks() if b[0] == 'figure'])} figures  ·  "
        f"{len([b for b in content.blocks() if b[0] == 'table'])} tables\n"
        "Placeholders in square brackets are filled in by the submitter."
    )
    style_run(run, size=9, color=GREY)
    document.add_page_break()


def render_toc(document: Document, chapter_pages: dict) -> None:
    heading = document.add_paragraph()
    run = heading.add_run("Table of Contents")
    style_run(run, size=15, bold=True, color=NAVY)
    heading.paragraph_format.space_after = Pt(12)

    for kind, payload in content.blocks():
        if kind == "h1":
            entry = document.add_paragraph()
            entry.paragraph_format.space_after = Pt(2)
            entry.paragraph_format.space_before = Pt(4)
            entry.paragraph_format.line_spacing = 1.0
            entry.paragraph_format.tab_stops.add_tab_stop(
                Inches(TEXT_W), WD_TAB_ALIGNMENT.RIGHT, leader=3
            )
            run = entry.add_run(f"{payload}\t{chapter_pages.get(payload, '')}")
            style_run(run, size=9.5, bold=True, color=NAVY)
        elif kind == "h2":
            entry = document.add_paragraph()
            entry.paragraph_format.space_after = Pt(0)
            entry.paragraph_format.space_before = Pt(0)
            entry.paragraph_format.line_spacing = 1.0
            entry.paragraph_format.left_indent = Inches(0.24)
            run = entry.add_run(payload)
            style_run(run, size=8, color=GREY)
    document.add_page_break()


NO_BREAK_H1 = ("References", "Appendix")


def render_block(document: Document, kind: str, payload,
                 on_new_page: bool = True) -> None:
    if kind == "h1":
        if on_new_page:
            heading = document.add_heading(payload, level=1)
        else:
            heading = document.add_paragraph()
            heading.paragraph_format.space_before = Pt(14)
            heading.paragraph_format.space_after = Pt(7)
            run = heading.add_run(payload)
            style_run(run, size=15, bold=True, color=NAVY)
            bottom_border(heading)
            return
        for run in heading.runs:
            style_run(run, size=15, bold=True, color=NAVY)
        bottom_border(heading)
    elif kind == "h2":
        heading = document.add_heading(payload, level=2)
        for run in heading.runs:
            style_run(run, size=12, bold=True, color=TEAL)
    elif kind == "h3":
        heading = document.add_heading(payload, level=3)
        for run in heading.runs:
            style_run(run, size=11, bold=True, color=NAVY)
    elif kind == "p":
        paragraph = document.add_paragraph(payload)
        paragraph.paragraph_format.space_after = Pt(6)
    elif kind == "bullets":
        for item in payload:
            paragraph = document.add_paragraph(item, style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(3)
    elif kind == "numbers":
        for item in payload:
            paragraph = document.add_paragraph(item, style="List Number")
            paragraph.paragraph_format.space_after = Pt(3)
    elif kind == "refs":
        for item in payload:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.32)
            paragraph.paragraph_format.first_line_indent = Inches(-0.32)
            paragraph.paragraph_format.space_after = Pt(4)
            paragraph.paragraph_format.line_spacing = 1.08
            run = paragraph.add_run(item)
            style_run(run, size=9.5)
    elif kind == "code":
        lines = payload.splitlines()
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(4)
        paragraph.paragraph_format.space_after = Pt(8)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.left_indent = Inches(0.08)
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        shade_paragraph(paragraph, "F5F7FA")
        for index, line in enumerate(lines):
            run = paragraph.add_run(line)
            style_run(run, size=8, font="Consolas")
            if index != len(lines) - 1:
                run.add_break()
    elif kind == "figure":
        image = HERE / payload["path"]
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.add_run().add_picture(str(image), width=Inches(payload["width_in"]))
        caption = document.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption.paragraph_format.space_after = Pt(12)
        run = caption.add_run(payload["caption"])
        style_run(run, size=8, italic=True, color=GREY)
    elif kind == "table":
        render_table(document, payload)
    elif kind == "pagebreak":
        document.add_page_break()


def render_table(document: Document, payload: dict) -> None:
    table = document.add_table(rows=1, cols=len(payload["header"]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    header_cells = table.rows[0].cells
    for cell, text, width in zip(header_cells, payload["header"],
                                 payload["widths"]):
        cell.width = Inches(width)
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(1)
        paragraph.paragraph_format.line_spacing = 1.0
        run = paragraph.add_run(text)
        style_run(run, size=8.5, bold=True, color=WHITE)
        set_cell_shading(cell, "16324F")

    for row_index, row in enumerate(payload["rows"]):
        cells = table.add_row().cells
        for cell, text, width in zip(cells, row, payload["widths"]):
            cell.width = Inches(width)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.paragraph_format.line_spacing = 1.0
            run = paragraph.add_run(text)
            style_run(run, size=8.5,
                      color=RGBColor(0x1A, 0x20, 0x2C))
            if row_index % 2 == 1:
                set_cell_shading(cell, "F4F7FA")

    caption = document.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_before = Pt(3)
    caption.paragraph_format.space_after = Pt(12)
    run = caption.add_run(payload["caption"])
    style_run(run, size=8, italic=True, color=GREY)


def shade_paragraph(paragraph, hex_fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    p_pr.append(shd)


def bottom_border(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), "2E86AB")
    borders.append(bottom)
    p_pr.append(borders)


# ── Main ──────────────────────────────────────────────────────
def main() -> int:
    blocks = content.blocks()

    # Attach the aspect ratio of every figure so the estimate is accurate.
    try:
        from PIL import Image
        for kind, payload in blocks:
            if kind == "figure":
                with Image.open(HERE / payload["path"]) as image:
                    payload["aspect"] = image.height / image.width
    except ImportError:
        pass

    # Pagination: title page = 1, table of contents = 2, body starts at 3.
    toc_height = 0.7 + sum(
        0.26 if kind == "h1" else 0.145
        for kind, _ in blocks if kind in ("h1", "h2")
    )
    toc_pages = max(1, math.ceil(toc_height / USABLE_H))
    body_start = 2 + toc_pages
    chapter_pages, last_page, _ = estimate(blocks, start_page=body_start)
    total_pages = last_page

    document = Document()
    configure_styles(document)
    section = document.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(PAGE_H)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, attr, Inches(MARGIN))
    add_footer(section, content.SHORT_TITLE)

    render_title_page(document, total_pages)
    render_toc(document, chapter_pages)
    for kind, payload in blocks:
        on_new_page = not (kind == "h1"
                           and str(payload).startswith(NO_BREAK_H1))
        render_block(document, kind, payload, on_new_page)

    document.save(OUT)

    print(f"wrote {OUT.relative_to(HERE.parent)}")
    print(f"  estimated length : {total_pages} pages "
          f"(title 1 + contents {toc_pages} + body {total_pages - 1 - toc_pages})")
    print("  chapter start pages:")
    for title, page in chapter_pages.items():
        print(f"    p.{page:>3}  {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
