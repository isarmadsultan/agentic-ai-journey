#!/usr/bin/env python3
"""
Notes Creator Agent
-------------------
Converts a final lecture explanation .txt file into a beautifully
formatted, fully readable PDF document.

No summarization. No LLM. Every word from the explanation appears
in the PDF, laid out cleanly with proper typography.

The parser detects:
  - The document title  (from the header block)
  - CAPS section headers  (e.g.  "INTRODUCTION", "WHAT IS X")
  - Normal body paragraphs
  - The KEY TAKEAWAYS section  (rendered as a styled list)

Usage:
    python notes_creator.py <explanation-file>

    Example:
        python notes_creator.py outputs\\machine-learning\\explanation.txt

Output:
    notes.pdf  (same directory as input)

Requires:
    pip install reportlab
"""

import sys
import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, KeepTogether
)


# ─── Colour Palette ───────────────────────────────────────────────────────────

class C:
    ACCENT       = colors.HexColor("#2D6BF4")
    ACCENT_DARK  = colors.HexColor("#1A3E96")
    ACCENT_LIGHT = colors.HexColor("#EEF3FE")
    CARD_BORDER  = colors.HexColor("#D6E4FF")
    TEXT_DARK    = colors.HexColor("#1C2B4A")
    TEXT_MID     = colors.HexColor("#445570")
    TEXT_LIGHT   = colors.HexColor("#7A8FA6")
    TAKEAWAY_BG  = colors.HexColor("#1A3E96")
    TAKEAWAY_FG  = colors.white
    HR           = colors.HexColor("#D6E4FF")
    WHITE        = colors.white


# ─── Styles ───────────────────────────────────────────────────────────────────

def build_styles():
    B = "Helvetica-Bold"
    R = "Helvetica"

    return {
        # Cover
        "title": ParagraphStyle(
            "title", fontName=B, fontSize=30, leading=38,
            textColor=C.ACCENT_DARK, alignment=TA_CENTER, spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", fontName=R, fontSize=12, leading=18,
            textColor=C.TEXT_MID, alignment=TA_CENTER, spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta", fontName=R, fontSize=9, leading=13,
            textColor=C.TEXT_LIGHT, alignment=TA_CENTER,
        ),
        "outline_title": ParagraphStyle(
            "outline_title", fontName=B, fontSize=11, leading=14,
            textColor=C.ACCENT_DARK, alignment=TA_LEFT, spaceAfter=6,
        ),
        "outline_item": ParagraphStyle(
            "outline_item", fontName=R, fontSize=10.5, leading=14,
            textColor=C.TEXT_DARK, alignment=TA_LEFT,
        ),
        "outline_time": ParagraphStyle(
            "outline_time", fontName=B, fontSize=10, leading=14,
            textColor=C.TEXT_MID, alignment=TA_LEFT,
        ),
        "outline_obj_header": ParagraphStyle(
            "outline_obj_header", fontName=B, fontSize=10.5, leading=14,
            textColor=C.TEXT_MID, alignment=TA_LEFT, spaceBefore=6, spaceAfter=2,
        ),

        # Section header
        "section_heading": ParagraphStyle(
            "section_heading", fontName=B, fontSize=13, leading=17,
            textColor=C.WHITE,
        ),

        # Body text — full justification, comfortable leading
        "body": ParagraphStyle(
            "body", fontName=R, fontSize=11, leading=18,
            textColor=C.TEXT_DARK, alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName=R, fontSize=11, leading=18,
            textColor=C.TEXT_DARK, alignment=TA_LEFT,
            leftIndent=14, firstLineIndent=-8, spaceAfter=4,
        ),

        # Takeaway items
        "takeaway_header": ParagraphStyle(
            "takeaway_header", fontName=B, fontSize=12, leading=16,
            textColor=C.TAKEAWAY_FG, alignment=TA_CENTER, spaceAfter=8,
        ),
        "takeaway_item": ParagraphStyle(
            "takeaway_item", fontName=R, fontSize=11, leading=17,
            textColor=C.TAKEAWAY_FG, leftIndent=10,
        ),

        # Footer
        "footer": ParagraphStyle(
            "footer", fontName=R, fontSize=8, leading=10,
            textColor=C.TEXT_LIGHT, alignment=TA_CENTER,
        ),
    }


# ─── Document Parser ──────────────────────────────────────────────────────────

def parse_explanation(raw_text: str) -> dict:
    """
    Parse the explanation .txt into a structured dict:
    {
        "title":    str,
        "sections": [
            { "heading": str | None, "paragraphs": [str] }
        ],
        "takeaways": [str]
    }
    """
    lines = raw_text.splitlines()

    def strip_inline_md(text: str) -> str:
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)
        return text.replace("`", "")

    def strip_wrapping_md(text: str) -> str:
        s = text.strip()
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"^\*{1,3}(.+?)\*{1,3}$", r"\1", s)
        s = re.sub(r"^_{1,3}(.+?)_{1,3}$", r"\1", s)
        return s.strip()

    def is_meta_line(s: str) -> bool:
        for prefix in ("Generated :", "Revised   :", "Model     :",
                       "Source    :", "Critique  :"):
            if s.startswith(prefix):
                return True
        return False

    def is_separator_line(s: str) -> bool:
        return bool(s) and len(s) >= 4 and not re.search(r"[A-Za-z0-9]", s)

    # Strip the file header block (lines until second === separator)
    body_lines = []
    in_header = True
    eq_count = 0
    meta_parts = []

    for line in lines:
        stripped = line.strip()
        if in_header:
            if re.match(r"^[=]{4,}$", stripped):
                eq_count += 1
                if eq_count >= 2:
                    in_header = False
                continue
            if is_meta_line(stripped):
                meta_parts.append(stripped)
            continue
        if is_meta_line(stripped):
            continue
        if stripped in ("LECTURE EXPLANATION",):
            continue
        body_lines.append(line)

    # Detect title: prefer specific Source metadata, fallback to first title line
    title = ""

    for m in meta_parts:
        if "Source" in m:
            src = m.split(":", 1)[-1].strip()
            if src.lower() in ("outline.txt", "explanation.txt", "outline", "explanation"):
                continue
            src = re.sub(r"-outline\.txt$|-explanation\.txt$", "", src, flags=re.I)
            src = re.sub(r"\.(txt|pdf)$", "", src, flags=re.I)
            title = re.sub(r"[-_]", " ", src).strip().title()
            break

    GENERIC = {"WHAT THIS LECTURE COVERS", "LECTURE EXPLANATION"}
    if not title:
        for bl in body_lines:
            s = strip_wrapping_md(bl)
            s = strip_inline_md(s).strip()
            if not s or s.upper() in GENERIC:
                continue
            if is_separator_line(s):
                continue
            if len(s) <= 90:
                title = s.strip()
                break

    # Walk body lines -> sections
    def is_section_header(line: str) -> bool:
        s = strip_wrapping_md(line)
        if not s or len(s) < 3:
            return False
        if is_separator_line(s):
            return False
        if s.upper() in GENERIC:
            return False
        allowed = re.sub(r"[A-Z0-9 :(),/&'\-]", "", s)
        if len(allowed) == 0 and any(c.isalpha() for c in s):
            return True

        raw = line.strip()
        if raw.startswith("**") and raw.endswith("**"):
            words = re.findall(r"[A-Za-z0-9']+", s)
            return 1 <= len(words) <= 8 and not s.endswith(".")

        words = re.findall(r"[A-Za-z0-9']+", s)
        if 1 <= len(words) <= 8 and not s.endswith("."):
            title_case = all((w[0].isupper() or w.isupper()) for w in words if w[0].isalpha())
            return title_case

        return False

    sections = []
    current_heading = None
    current_paras = []
    buffer = []

    def flush():
        nonlocal buffer
        text = " ".join(buffer).strip()
        if text:
            current_paras.append(strip_inline_md(text))
        buffer.clear()

    for line in body_lines:
        stripped = line.strip()
        normalized = strip_wrapping_md(stripped)

        if is_separator_line(stripped):
            flush()
            continue

        if is_section_header(stripped):
            flush()
            if current_paras or current_heading:
                sections.append({"heading": current_heading,
                                  "paragraphs": current_paras[:]})
            heading_text = strip_inline_md(normalized)
            current_heading = heading_text if heading_text else normalized.title()
            current_paras = []
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        number_match = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if bullet_match:
            flush()
            bullet_text = strip_inline_md(bullet_match.group(1).strip())
            if bullet_text:
                current_paras.append(f"- {bullet_text}")
            continue
        if number_match:
            flush()
            bullet_text = strip_inline_md(number_match.group(2).strip())
            if bullet_text:
                current_paras.append(f"{number_match.group(1)}. {bullet_text}")
            continue

        if stripped == "":
            flush()
        else:
            buffer.append(strip_inline_md(stripped))

    flush()
    if current_paras or current_heading:
        sections.append({"heading": current_heading,
                          "paragraphs": current_paras[:]})

    # Split KEY TAKEAWAYS into a separate list
    takeaways = []
    clean_sections = []
    for sec in sections:
        h = (sec["heading"] or "").upper()
        if "TAKEAWAY" in h:
            for p in sec["paragraphs"]:
                parts = re.split(r"\s*\d+[.)]\s+", p)
                for part in parts:
                    part = part.strip()
                    if part:
                        takeaways.append(part)
        else:
            clean_sections.append(sec)

    return {
        "title": title or "Lecture Explanation",
        "sections": clean_sections,
        "takeaways": takeaways,
    }


def parse_outline(outline_path: str):
    if not outline_path or not os.path.exists(outline_path):
        return None

    with open(outline_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    section_re = re.compile(r"^(?P<num>[IVX]+)\.\s+(?P<title>.+?)(?:\s+\((?P<time>[^)]+)\))?\s*$")
    topic = ""
    objectives = []
    sections = []
    in_objectives = False

    for line in lines:
        s = line.strip()
        if not s:
            if in_objectives:
                in_objectives = False
            continue

        if s.startswith("Topic"):
            parts = s.split(":", 1)
            if len(parts) == 2:
                topic = parts[1].strip()
            continue

        if s.startswith("Objectives"):
            in_objectives = True
            continue

        if in_objectives:
            if s.startswith(("*", "-")):
                objectives.append(s.lstrip("*- ").strip())
                continue
            if section_re.match(s):
                in_objectives = False
            else:
                continue

        match = section_re.match(s)
        if match:
            title = match.group("title").strip()
            time = (match.group("time") or "").strip()
            sections.append({"title": title, "time": time})

    return {
        "topic": topic,
        "objectives": objectives,
        "sections": sections,
    }

# ─── PDF Builders ─────────────────────────────────────────────────────────────

def safe(text: str) -> str:
    """Escape XML special characters for ReportLab Paragraph."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def build_outline_block(outline_data: dict, styles, content_w: float) -> list:
    if not outline_data:
        return []

    inner = []
    inner.append(Paragraph("LECTURE OUTLINE", styles["outline_title"]))

    rows = []
    for sec in outline_data.get("sections", []):
        title = sec.get("title", "").strip()
        time = sec.get("time", "").strip()
        if not title:
            continue
        rows.append([
            Paragraph(safe(title), styles["outline_item"]),
            Paragraph(safe(time), styles["outline_time"]),
        ])

    if rows:
        outline_table = Table(
            rows,
            colWidths=[content_w * 0.72, content_w * 0.28],
            hAlign="LEFT",
            style=TableStyle([
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",(0, 0), (-1, -1), 0),
                ("TOPPADDING",  (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
            ]),
        )
        inner.append(outline_table)

    objectives = outline_data.get("objectives", [])
    if objectives:
        inner.append(Spacer(1, 0.2 * cm))
        inner.append(Paragraph("LEARNING OBJECTIVES", styles["outline_obj_header"]))
        for obj in objectives:
            inner.append(Paragraph(safe(f"- {obj}"), styles["bullet"]))

    card = Table(
        [[inner]],
        colWidths=[content_w],
        style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C.ACCENT_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 0.75, C.CARD_BORDER),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]),
    )

    return [card, Spacer(1, 0.6 * cm)]


def build_cover(doc_data: dict, styles, content_w: float, outline_data) -> list:
    story = []
    story.append(Spacer(1, 2.5 * cm))

    # Top rule
    story.append(Table([[""]], colWidths=[content_w], rowHeights=[5],
        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), C.ACCENT)])))
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph(safe(doc_data["title"]), styles["title"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Lecture Notes", styles["cover_sub"]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        f"Generated  ·  {datetime.now().strftime('%B %d, %Y')}",
        styles["cover_meta"]
    ))
    story.append(Spacer(1, 0.5 * cm))

    # Bottom rule
    story.append(Table([[""]], colWidths=[content_w], rowHeights=[5],
        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), C.ACCENT)])))

    if outline_data:
        story.append(Spacer(1, 0.5 * cm))
        story += build_outline_block(outline_data, styles, content_w)
    story.append(HRFlowable(width=content_w, thickness=0.6, color=C.HR, spaceBefore=4, spaceAfter=10))
    return story


def build_section_block(sec: dict, styles, content_w: float) -> list:
    """Blue header bar (if heading exists) + body paragraphs."""
    block = []

    if sec["heading"]:
        para = Paragraph(safe(sec["heading"]), styles["section_heading"])
        hdr  = Table([[para]], colWidths=[content_w],
            style=TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), C.ACCENT),
                ("TOPPADDING",    (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING",   (0, 0), (-1, -1), 16),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ]))
        block.append(hdr)
        block.append(Spacer(1, 0.3 * cm))

    for para_text in sec["paragraphs"]:
        if not para_text.strip():
            continue
        if para_text.startswith("- ") or re.match(r"^\d+\.\s+", para_text):
            block.append(Paragraph(safe(para_text), styles["bullet"]))
        else:
            block.append(Paragraph(safe(para_text), styles["body"]))

    block.append(Spacer(1, 0.5 * cm))
    return block


def build_takeaways_block(takeaways: list, styles, content_w: float) -> list:
    if not takeaways:
        return []

    inner_rows = []
    inner_rows.append([Paragraph("★  KEY TAKEAWAYS", styles["takeaway_header"])])
    inner_rows.append([HRFlowable(
        width=content_w - 3 * cm, thickness=0.5,
        color=colors.HexColor("#3D5A99"), spaceAfter=6
    )])
    for i, item in enumerate(takeaways, 1):
        inner_rows.append([Paragraph(
            f'<font color="#7EB8F7"><b>{i}.</b></font>  {safe(item)}',
            styles["takeaway_item"]
        )])
        inner_rows.append([Spacer(1, 5)])

    tbl = Table(inner_rows, colWidths=[content_w],
        style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C.TAKEAWAY_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 20),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
        ]))

    outer = Table([[tbl]], colWidths=[content_w],
        style=TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("BACKGROUND",    (0, 0), (-1, -1), C.TAKEAWAY_BG),
        ]))

    return [outer, Spacer(1, 0.8 * cm)]


def page_decorations(canvas, doc):
    """Accent rule header + page number footer on every page after the cover."""
    if doc.page == 1:
        return
    canvas.saveState()
    pw, ph = A4

    canvas.setStrokeColor(C.ACCENT)
    canvas.setLineWidth(1.5)
    canvas.line(2 * cm, ph - 1.2 * cm, pw - 2 * cm, ph - 1.2 * cm)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C.TEXT_LIGHT)
    canvas.drawCentredString(pw / 2, 1.2 * cm, f"Page {doc.page}")

    canvas.setStrokeColor(C.HR)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.6 * cm, pw - 2 * cm, 1.6 * cm)

    canvas.restoreState()


# ─── Main Renderer ────────────────────────────────────────────────────────────

def render_pdf(explanation_path: str, output_path: str) -> None:
    with open(explanation_path, "r", encoding="utf-8") as f:
        raw = f.read()

    doc_data = parse_explanation(raw)
    outline_path = derive_outline_path(explanation_path)
    outline_data = parse_outline(outline_path)
    if outline_data and outline_data.get("topic"):
        doc_data["title"] = outline_data["topic"]
    print(f"[INFO] Title     : {doc_data['title']}")
    print(f"[INFO] Sections  : {len(doc_data['sections'])}")
    print(f"[INFO] Takeaways : {len(doc_data['takeaways'])}")

    pw, ph    = A4
    margin_lr = 2.2 * cm
    margin_tb = 2.2 * cm
    content_w = pw - 2 * margin_lr

    pdf = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=margin_lr,  rightMargin=margin_lr,
        topMargin=margin_tb,   bottomMargin=margin_tb + 0.4 * cm,
        title=doc_data["title"],
        author="Notes Creator Agent",
    )

    styles = build_styles()
    story  = []

    # Cover
    story += build_cover(doc_data, styles, content_w, outline_data)

    # Body sections
    for sec in doc_data["sections"]:
        block = build_section_block(sec, styles, content_w)
        if sec["heading"] and len(block) > 2:
            # Keep header glued to first paragraph
            story.append(KeepTogether(block[:3]))
            story += block[3:]
        else:
            story += block

    # Takeaways
    story += build_takeaways_block(doc_data["takeaways"], styles, content_w)

    pdf.build(story, onFirstPage=page_decorations, onLaterPages=page_decorations)
    print(f"[SUCCESS] PDF saved to: {output_path}")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def derive_output_path(explanation_path: str) -> str:
    directory = os.path.dirname(os.path.abspath(explanation_path))
    basename  = os.path.basename(explanation_path)
    if basename == "explanation.txt":
        return os.path.join(directory, "notes.pdf")
    if basename.endswith("-explanation.txt"):
        slug = basename[: -len("-explanation.txt")]
    else:
        slug = os.path.splitext(basename)[0]
    return os.path.join(directory, f"{slug}-notes.pdf")


def derive_outline_path(explanation_path: str) -> str:
    directory = os.path.dirname(os.path.abspath(explanation_path))
    basename = os.path.basename(explanation_path)
    if basename == "explanation.txt":
        return os.path.join(directory, "outline.txt")
    if basename.endswith("-explanation.txt"):
        slug = basename[: -len("-explanation.txt")]
        return os.path.join(directory, f"{slug}-outline.txt")
    return os.path.join(directory, "outline.txt")


def main():
    if len(sys.argv) < 2:
        print("\nUsage: python notes_creator.py <explanation-file>")
        print("Example: python notes_creator.py outputs\\machine-learning\\explanation.txt\n")
        sys.exit(1)

    explanation_path = sys.argv[1]

    if not os.path.exists(explanation_path):
        print(f"[ERROR] File not found: {explanation_path}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  NOTES CREATOR")
    print("=" * 60)
    print(f"[INFO] Input : {explanation_path}")

    output_path = derive_output_path(explanation_path)
    print(f"[INFO] Output: {output_path}\n")

    render_pdf(explanation_path, output_path)
    print(f"\n[DONE] Open: {output_path}")


if __name__ == "__main__":
    main()
