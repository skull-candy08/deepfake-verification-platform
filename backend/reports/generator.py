"""
generator.py — PDF Forensic Report Generator.

Produces a professional, multi-page PDF report summarising the results of
all forensic analysis modules run against a media file.

Page layout:
    1. **Executive Summary** — file metadata, final fused score (large),
       colour-coded tier badge, and verdict text.
    2. **Module Breakdown** — table listing each module, its score, and
       key findings.
    3+ **Evidence Gallery** — embedded evidence images (ELA heatmaps,
       spectrograms, etc.) with captions.

Typical usage::

    from backend.reports.generator import generate_report

    pdf_path = generate_report(analysis_results, output_dir="./reports")
    print(f"Report saved to {pdf_path}")
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch, mm
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 2.0 * cm

PLATFORM_NAME = "Deepfake Verification Platform"
PLATFORM_SUBTITLE = "Forensic Analysis Report"

# Tier colour mapping
TIER_COLOURS: Dict[str, colors.Color] = {
    "AUTHENTIC": colors.HexColor("#22c55e"),    # green
    "LIKELY AUTHENTIC": colors.HexColor("#22c55e"),
    "SUSPICIOUS": colors.HexColor("#f59e0b"),   # amber
    "LIKELY MANIPULATED": colors.HexColor("#ef4444"),  # red
    "MANIPULATED": colors.HexColor("#dc2626"),   # deep red
}

# Style presets
_styles = getSampleStyleSheet()


def _get_styles() -> Dict[str, ParagraphStyle]:
    """Build custom paragraph styles for the report."""
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=_styles["Title"],
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#1e293b"),
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=_styles["Normal"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "heading2": ParagraphStyle(
            "Heading2Custom",
            parent=_styles["Heading2"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
        ),
        "body_center": ParagraphStyle(
            "BodyCenter",
            parent=_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            alignment=TA_CENTER,
        ),
        "score_large": ParagraphStyle(
            "ScoreLarge",
            parent=_styles["Normal"],
            fontSize=48,
            leading=56,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "verdict": ParagraphStyle(
            "VerdictStyle",
            parent=_styles["Normal"],
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=16,
        ),
        "caption": ParagraphStyle(
            "CaptionStyle",
            parent=_styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
    }


def _header_footer(canvas, doc):
    """Draw a consistent header and footer on every page."""
    canvas.saveState()

    # Header line
    canvas.setStrokeColor(colors.HexColor("#3b82f6"))
    canvas.setLineWidth(2)
    canvas.line(MARGIN, PAGE_HEIGHT - MARGIN + 10, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN + 10)

    # Header text
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.HexColor("#3b82f6"))
    canvas.drawString(MARGIN, PAGE_HEIGHT - MARGIN + 14, PLATFORM_NAME.upper())

    # Footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(MARGIN, MARGIN - 14, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, MARGIN - 14, f"Page {doc.page}")

    canvas.restoreState()


def _build_executive_summary(
    analysis_results: Dict[str, Any],
    styles: Dict[str, ParagraphStyle],
) -> List[Any]:
    """Build flowables for Page 1 — Executive Summary."""
    elements: List[Any] = []

    elements.append(Spacer(1, 1.5 * cm))
    elements.append(Paragraph(PLATFORM_NAME, styles["title"]))
    elements.append(Paragraph(PLATFORM_SUBTITLE, styles["subtitle"]))
    elements.append(Spacer(1, 0.5 * cm))

    # File information table
    file_id = analysis_results.get("file_id", "N/A")
    filename = analysis_results.get("filename", "N/A")
    media_type = analysis_results.get("media_type", "N/A")
    timestamp = analysis_results.get("timestamp", datetime.now().isoformat())

    info_data = [
        ["File ID", str(file_id)],
        ["Filename", str(filename)],
        ["Media Type", str(media_type).upper()],
        ["Analysis Date", str(timestamp)],
    ]
    info_table = Table(info_data, colWidths=[4.5 * cm, 11 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1e293b")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 1.2 * cm))

    # ── Large score display ──────────────────────────────────────────────
    fused_score: float = analysis_results.get("fused_score", 0.0)
    tier_data = analysis_results.get("tier", "UNKNOWN")
    tier_label = tier_data.get("label", "UNKNOWN") if isinstance(tier_data, dict) else str(tier_data)
    verdict: str = analysis_results.get("verdict", "No verdict available")

    tier_colour = TIER_COLOURS.get(tier_label.upper(), colors.HexColor("#64748b"))
    score_style = ParagraphStyle(
        "ScoreDynamic",
        parent=styles["score_large"],
        textColor=tier_colour,
    )
    elements.append(Paragraph(f"{fused_score:.2f}", score_style))
    elements.append(Paragraph("Manipulation Probability Score", styles["body_center"]))
    elements.append(Spacer(1, 0.4 * cm))

    # Tier badge
    tier_text = f'<font color="{tier_colour.hexval()}">' \
                f'<b>[ {tier_label.upper()} ]</b></font>'
    elements.append(Paragraph(tier_text, styles["verdict"]))

    # Verdict paragraph
    elements.append(Paragraph(verdict, styles["body_center"]))
    elements.append(Spacer(1, 1.0 * cm))

    # Scale legend
    scale_data = [
        ["0.0 – 0.3", "0.3 – 0.5", "0.5 – 0.7", "0.7 – 1.0"],
        ["Authentic", "Likely Authentic", "Suspicious", "Manipulated"],
    ]
    scale_table = Table(scale_data, colWidths=[3.8 * cm] * 4)
    scale_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#dcfce7")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fef9c3")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#fed7aa")),
        ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#fecaca")),
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#dcfce7")),
        ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#fef9c3")),
        ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#fed7aa")),
        ("BACKGROUND", (3, 1), (3, 1), colors.HexColor("#fecaca")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(scale_table)

    return elements


def _build_module_breakdown(
    analysis_results: Dict[str, Any],
    styles: Dict[str, ParagraphStyle],
) -> List[Any]:
    """Build flowables for Page 2 — Module Breakdown table."""
    elements: List[Any] = []

    elements.append(PageBreak())
    elements.append(Paragraph("Module Breakdown", styles["heading2"]))
    elements.append(Spacer(1, 0.3 * cm))

    module_scores: Dict[str, Dict[str, Any]] = analysis_results.get(
        "module_scores", {}
    )

    # Table header
    header = ["Module", "Score", "Key Findings"]
    rows = [header]

    for module_name, module_result in module_scores.items():
        score_val: float = module_result.get("score", 0.0)
        details: Dict[str, Any] = module_result.get("details", {})

        # Pick the most interesting detail items for the summary column
        findings_parts: List[str] = []
        for key, val in list(details.items())[:5]:
            if key in ("error", "note"):
                findings_parts.append(f"{val}")
            elif isinstance(val, (int, float)):
                findings_parts.append(f"{key}: {val}")
            elif isinstance(val, str) and len(val) < 80:
                findings_parts.append(f"{key}: {val}")
            elif isinstance(val, bool):
                findings_parts.append(f"{key}: {'Yes' if val else 'No'}")
            elif isinstance(val, list) and len(val) <= 3:
                findings_parts.append(f"{key}: {val}")

        findings_text = "; ".join(findings_parts) if findings_parts else "—"
        # Truncate long findings
        if len(findings_text) > 120:
            findings_text = findings_text[:117] + "..."

        pretty_name = module_name.replace("_", " ").title()
        rows.append([pretty_name, f"{score_val:.4f}", findings_text])

    col_widths = [4.0 * cm, 2.5 * cm, 9.5 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)

    # Colour-code score cells
    table_style_commands = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]

    # Row-based score colouring
    for row_idx in range(1, len(rows)):
        try:
            score_val = float(rows[row_idx][1])
        except (ValueError, IndexError):
            continue
        if score_val < 0.3:
            bg = colors.HexColor("#dcfce7")
        elif score_val < 0.5:
            bg = colors.HexColor("#fef9c3")
        elif score_val < 0.7:
            bg = colors.HexColor("#fed7aa")
        else:
            bg = colors.HexColor("#fecaca")
        table_style_commands.append(("BACKGROUND", (1, row_idx), (1, row_idx), bg))

    # Alternate row shading
    for row_idx in range(1, len(rows)):
        if row_idx % 2 == 0:
            table_style_commands.append(
                ("BACKGROUND", (0, row_idx), (0, row_idx), colors.HexColor("#f8fafc"))
            )
            table_style_commands.append(
                ("BACKGROUND", (2, row_idx), (2, row_idx), colors.HexColor("#f8fafc"))
            )

    table.setStyle(TableStyle(table_style_commands))
    elements.append(table)

    return elements


def _build_evidence_pages(
    analysis_results: Dict[str, Any],
    styles: Dict[str, ParagraphStyle],
) -> List[Any]:
    """Build flowables for Page 3+ — Evidence Gallery."""
    elements: List[Any] = []

    module_scores: Dict[str, Dict[str, Any]] = analysis_results.get(
        "module_scores", {}
    )

    # Collect all evidence images across modules
    evidence_items: List[tuple[str, str]] = []  # (module_name, image_path)
    for module_name, module_result in module_scores.items():
        for img_path in module_result.get("evidence", []):
            if os.path.isfile(img_path):
                evidence_items.append((module_name, img_path))

    if not evidence_items:
        return elements

    elements.append(PageBreak())
    elements.append(Paragraph("Evidence Gallery", styles["heading2"]))
    elements.append(Spacer(1, 0.3 * cm))

    max_img_width = PAGE_WIDTH - 2 * MARGIN - 1 * cm
    max_img_height = 8.0 * cm

    for module_name, img_path in evidence_items:
        pretty_module = module_name.replace("_", " ").title()
        img_filename = Path(img_path).name

        elements.append(
            Paragraph(f"<b>{pretty_module}</b> — {img_filename}", styles["body"])
        )
        elements.append(Spacer(1, 0.2 * cm))

        try:
            img = RLImage(img_path)
            # Scale to fit within bounds while preserving aspect ratio
            iw, ih = img.drawWidth, img.drawHeight
            if iw <= 0 or ih <= 0:
                iw, ih = max_img_width, max_img_height
            ratio = min(max_img_width / iw, max_img_height / ih, 1.0)
            img.drawWidth = iw * ratio
            img.drawHeight = ih * ratio
            img.hAlign = "CENTER"
            elements.append(img)
        except Exception as exc:
            logger.warning("generator: cannot embed image %s — %s", img_path, exc)
            elements.append(
                Paragraph(f"<i>[Image could not be embedded: {exc}]</i>", styles["body"])
            )

        elements.append(Spacer(1, 0.2 * cm))
        elements.append(
            Paragraph(f"Source: {img_path}", styles["caption"])
        )
        elements.append(Spacer(1, 0.5 * cm))

    return elements


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(
    analysis_results: Dict[str, Any],
    output_dir: str,
) -> str:
    """Generate a PDF forensic report and return its file path.

    Parameters
    ----------
    analysis_results : dict
        Must contain::

            {
                "file_id": str,
                "filename": str,
                "media_type": str,          # "image", "video", "audio"
                "module_scores": {
                    "module_name": {
                        "score": float,
                        "details": dict,
                        "evidence": list[str],
                    },
                    ...
                },
                "fused_score": float,       # 0.0 – 1.0
                "tier": str,                # e.g. "SUSPICIOUS"
                "verdict": str,             # human-readable verdict
                "timestamp": str,           # ISO-8601
            }

    output_dir : str
        Directory where the PDF will be written.

    Returns
    -------
    str
        Absolute path to the generated PDF file.
    """
    logger.info("generator: building report for file_id=%s", analysis_results.get("file_id"))

    os.makedirs(output_dir, exist_ok=True)

    report_id = uuid.uuid4()
    pdf_filename = f"forensic_report_{report_id}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 0.5 * cm,
        bottomMargin=MARGIN,
        title=f"{PLATFORM_NAME} — Report {report_id}",
        author=PLATFORM_NAME,
    )

    styles = _get_styles()
    elements: List[Any] = []

    # Page 1 — Executive Summary
    elements.extend(_build_executive_summary(analysis_results, styles))

    # Page 2 — Module Breakdown
    elements.extend(_build_module_breakdown(analysis_results, styles))

    # Page 3+ — Evidence Gallery
    elements.extend(_build_evidence_pages(analysis_results, styles))

    # Build PDF
    try:
        doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    except Exception as exc:
        logger.error("generator: PDF build failed — %s", exc)
        raise RuntimeError(f"PDF report generation failed: {exc}") from exc

    abs_path = os.path.abspath(pdf_path)
    logger.info("generator: report saved → %s", abs_path)
    return abs_path
