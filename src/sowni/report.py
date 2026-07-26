from __future__ import annotations

from pathlib import Path


CLASSIFICATION_LABELS = {
    "direct_designation": "Confirmed direct designation in loaded data",
    "ownership_derived_candidate": "Potential ownership-derived blocking",
    "control_related_exposure": "Control-related exposure",
    "no_material_indicator": "No material indicator identified",
}


def render_markdown(result: dict) -> str:
    target = result.get("target_entity") or {}
    classification = result["classification"]
    lines = [
        "# Sanctions Ownership Network Investigation Brief",
        "",
        "> **Analytical screening output — not legal advice or a final compliance determination.**",
        "",
        f"- **Generated:** {result['generated_at']}",
        f"- **Run ID:** `{result['run_id']}`",
        f"- **Mode:** {result['mode']}",
        f"- **Query:** {result['query']}",
        f"- **Target:** {target.get('name', 'Unresolved')}",
        f"- **Classification:** {CLASSIFICATION_LABELS.get(classification, classification)}",
        f"- **Data confidence:** {result['data_confidence']}",
        "",
        "## Executive finding",
        "",
        result["executive_finding"],
        "",
        "## Ownership analysis",
        "",
    ]
    ownership = result.get("ownership_finding")
    if ownership:
        lines.extend(
            [
                f"- Status: `{ownership['status']}`",
                f"- Aggregate ownership in loaded graph: {ownership['aggregate_pct']:.2f}%",
                f"- Identified owner IDs: {', '.join(ownership['blocked_owner_ids']) or 'Direct designation'}",
                f"- Propagation iteration: {ownership['iteration']}",
                f"- Explanation: {ownership['explanation']}",
            ]
        )
    else:
        lines.append("- No ownership-derived designation candidate was found in the loaded graph.")

    path = result.get("ownership_path", [])
    if path:
        lines.extend(["", f"- Ownership path to designation: `{' → '.join(path)}`"])

    enrichment = result.get("identity_enrichment")
    if enrichment:
        lines.extend(
            [
                "",
                "## GLEIF identity enrichment",
                "",
                f"- Selected legal name: {enrichment['selected_name']}",
                f"- LEI: `{enrichment['selected_lei']}`",
                f"- Related entities loaded: {enrichment['entity_count']}",
                f"- Accounting-parent links loaded: {enrichment['relationship_count']}",
                f"- Scope: {enrichment['scope_note']}",
            ]
        )
        for warning in enrichment.get("warnings", []):
            lines.append(f"- Data note: {warning}")

    lines.extend(["", "## Name-screening candidates", ""])
    matches = result.get("matches", [])
    if matches:
        lines.extend(
            [
                "| Candidate | Matched name | Score | Designated | Reasons |",
                "|---|---|---:|:---:|---|",
            ]
        )
        for match in matches:
            reasons = "; ".join(match["reasons"])
            lines.append(
                f"| {match['entity_name']} | {match['matched_name']} | "
                f"{match['score']:.2f} | {'Yes' if match['designated'] else 'No'} | "
                f"{reasons} |"
            )
    else:
        lines.append("No candidate exceeded the configured screening threshold.")

    lines.extend(["", "## Investigative indicators", ""])
    for indicator in result.get("indicators", []):
        lines.append(f"- **{indicator['title']}:** {indicator['detail']}")
    if not result.get("indicators"):
        lines.append("- No additional indicators were produced.")

    lines.extend(["", "## Recommended analyst actions", ""])
    for action in result["recommended_actions"]:
        lines.append(f"- {action}")

    lines.extend(
        [
            "",
            "## Data and methodology limitations",
            "",
            "- A sanctions-list match is a candidate for analyst review, not proof of identity.",
            "- Ownership calculations are only as complete and current as the loaded relationships.",
            "- Control and ownership are reported separately.",
            "- GLEIF direct and ultimate parents are accounting-consolidation relationships, not percentage-ownership evidence.",
            "- Shared addresses and offshore-dataset appearances are investigative leads, not evidence of misconduct.",
            "- Effective dates, aggregation rules, program-specific restrictions, licenses, and legal guidance require validation.",
            "",
            "## Source register",
            "",
        ]
    )
    for source in result["sources"]:
        lines.append(
            f"- **{source['name']}** — {source['url']} "
            f"(retrieved/represented: {source['retrieved_at']})"
        )
    if result["mode"] == "sample":
        lines.extend(
            [
                "",
                "> The bundled demonstration entities and relationships are fictional. "
                "They exist only to exercise the analytical workflow.",
            ]
        )
    return "\n".join(lines) + "\n"


def write_markdown(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(result), encoding="utf-8")


def write_pdf(result: dict, path: Path) -> bool:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    regular_font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold_font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    base_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    if regular_font_path.exists() and bold_font_path.exists():
        pdfmetrics.registerFont(TTFont("SONISans", str(regular_font_path)))
        pdfmetrics.registerFont(TTFont("SONISans-Bold", str(bold_font_path)))
        base_font = "SONISans"
        bold_font = "SONISans-Bold"

    styles = getSampleStyleSheet()
    for style_name in ("Normal", "BodyText"):
        styles[style_name].fontName = base_font
        styles[style_name].fontSize = 8.25
        styles[style_name].leading = 10.75
    for style_name in ("Title", "Heading1", "Heading2", "Heading3"):
        styles[style_name].fontName = bold_font
    styles["Heading1"].fontSize = 15
    styles["Heading1"].leading = 18
    styles["Heading1"].spaceBefore = 9
    styles["Heading1"].spaceAfter = 5
    styles["Heading2"].fontSize = 13
    styles["Heading2"].leading = 16
    styles["Heading2"].spaceBefore = 7
    styles["Heading2"].spaceAfter = 4
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324D"),
            fontSize=18,
            leading=22,
            spaceAfter=8,
            fontName=bold_font,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Disclaimer",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#8A2D2D"),
            backColor=colors.HexColor("#FBEAEA"),
            borderPadding=8,
            spaceAfter=12,
            fontName=base_font,
        )
    )
    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title="Sanctions Ownership Network Investigation Brief",
        author="Sanctions Ownership Network Investigator",
    )

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont(base_font, 8)
        canvas.setFillColor(colors.HexColor("#5E6B78"))
        canvas.drawRightString(
            letter[0] - 0.65 * inch,
            0.25 * inch,
            f"Page {document.page}",
        )
        canvas.restoreState()

    story = [
        Paragraph("Sanctions Ownership Network Investigation Brief", styles["TitleCenter"]),
        Paragraph(
            "Analytical screening output - not legal advice or a final compliance determination.",
            styles["Disclaimer"],
        ),
    ]
    target = result.get("target_entity") or {}
    overview = [
        ["Query", result["query"]],
        ["Target", target.get("name", "Unresolved")],
        ["Classification", CLASSIFICATION_LABELS.get(result["classification"], result["classification"])],
        ["Data confidence", result["data_confidence"]],
        ["Run ID", result["run_id"]],
    ]
    table = Table(overview, colWidths=[1.35 * inch, 5.55 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF5")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7C4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (0, -1), bold_font),
                ("FONTNAME", (1, 0), (1, -1), base_font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            table,
            Spacer(1, 7),
            Paragraph("Executive finding", styles["Heading2"]),
            Paragraph(result["executive_finding"], styles["BodyText"]),
            Spacer(1, 4),
            Paragraph("Ownership analysis", styles["Heading2"]),
        ]
    )
    finding = result.get("ownership_finding")
    if finding:
        ownership_text = (
            f"<b>Status:</b> {finding['status']}<br/>"
            f"<b>Aggregate loaded ownership:</b> {finding['aggregate_pct']:.2f}%<br/>"
            f"<b>Explanation:</b> {finding['explanation']}"
        )
        story.append(Paragraph(ownership_text, styles["BodyText"]))
    else:
        story.append(
            Paragraph(
                "No ownership-derived designation candidate was found in the loaded graph.",
                styles["BodyText"],
            )
        )

    enrichment = result.get("identity_enrichment")
    if enrichment:
        story.extend(
            [
                Spacer(1, 6),
                Paragraph("GLEIF identity enrichment", styles["Heading2"]),
                Paragraph(
                    f"<b>Selected entity:</b> {enrichment['selected_name']}<br/>"
                    f"<b>LEI:</b> {enrichment['selected_lei']}<br/>"
                    f"<b>Accounting-parent links:</b> "
                    f"{enrichment['relationship_count']}<br/>"
                    f"<b>Scope:</b> {enrichment['scope_note']}",
                    styles["BodyText"],
                ),
            ]
        )

    story.extend(
        [
            Spacer(1, 8),
            Paragraph("Screening candidates", styles["Heading2"]),
        ]
    )
    matches = result.get("matches", [])
    if matches:
        match_rows = [["Candidate", "Score", "Designated", "Reason"]]
        for match in matches[:10]:
            match_rows.append(
                [
                    Paragraph(match["entity_name"], styles["BodyText"]),
                    f"{match['score']:.2f}",
                    "Yes" if match["designated"] else "No",
                    Paragraph("; ".join(match["reasons"]), styles["BodyText"]),
                ]
            )
        matches_table = Table(
            match_rows, colWidths=[2.15 * inch, 0.65 * inch, 0.75 * inch, 3.35 * inch],
            repeatRows=1,
        )
        matches_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB7C4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), bold_font),
                    ("FONTNAME", (0, 1), (-1, -1), base_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(matches_table)
    else:
        story.append(
            Paragraph(
                "No candidate exceeded the configured screening threshold.",
                styles["BodyText"],
            )
        )

    story.extend([Spacer(1, 5), Paragraph("Indicators and actions", styles["Heading1"])])
    for indicator in result.get("indicators", []):
        story.append(
            Paragraph(
                f"<b>{indicator['title']}:</b> {indicator['detail']}",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 4))
    story.append(Paragraph("Recommended analyst actions", styles["Heading2"]))
    for action in result["recommended_actions"]:
        story.append(Paragraph(f"- {action}", styles["BodyText"]))

    story.append(Paragraph("Limitations", styles["Heading2"]))
    limitation = (
        "Matches require human review. Ownership calculations depend on the completeness "
        "and effective dates of loaded relationships. Control and ownership are separate. "
        "GLEIF accounting-parent links do not establish percentage ownership. "
        "Shared addresses and offshore-dataset appearances are investigative leads, not "
        "evidence of misconduct. Consult current official guidance and qualified counsel."
    )
    story.append(Paragraph(limitation, styles["BodyText"]))
    if result["mode"] == "sample":
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                "The bundled demonstration entities and relationships are fictional.",
                styles["Disclaimer"],
            )
        )
    document.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return True
