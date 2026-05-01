"""Utility functions for PDF parsing, chart generation, and PDF export."""

from __future__ import annotations

import datetime
import unicodedata
from typing import Any

import pdfplumber
import plotly.graph_objects as go


def _sanitize_for_pdf(text: str) -> str:
    """Replace Unicode characters that Helvetica can't render with ASCII equivalents."""
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00a0": " ",    # non-breaking space
        "\u2010": "-",    # hyphen
        "\u2011": "-",    # non-breaking hyphen
        "\u2012": "-",    # figure dash
        "\u00b7": "*",    # middle dot
        "\u2032": "'",    # prime
        "\u2033": '"',    # double prime
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Strip any remaining non-latin1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")

# ---------------------------------------------------------------------------
# Airbnb brand colors
# ---------------------------------------------------------------------------
CORAL = "#FF5A5F"
TEAL = "#00A699"
DARK = "#484848"
GRAY = "#767676"
LIGHT_GRAY = "#E0E0E0"
WHITE = "#FFFFFF"

DIMENSION_LABELS = {
    "tco_budget_fit": "TCO & Budget Fit",
    "pricing_vs_benchmark": "Pricing vs Benchmark",
    "risk_profile": "Risk Profile",
    "integration_readiness": "Integration Readiness",
    "operational_reliability": "Operational Reliability",
    "strategic_optionality": "Strategic Optionality",
    "esg_diversity": "ESG & Diversity",
}


def parse_pdf(uploaded_file) -> str:
    """Extract text from an uploaded PDF file."""
    try:
        text_parts: list[str] = []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception as e:
        return ""


def _get_scores_from_extracted(extracted: dict) -> dict[str, float]:
    """Pull numeric scores out of an extraction result."""
    scores_section = extracted.get("scores", {})
    result = {}
    for key in DIMENSION_LABELS:
        entry = scores_section.get(key, {})
        val = entry.get("score", 0)
        try:
            result[key] = float(val)
        except (TypeError, ValueError):
            result[key] = 0.0
    return result


def compute_weighted_score(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Compute a 0-100 weighted score from dimension scores (0-10) and weights (summing to 100)."""
    total = 0.0
    for dim, weight in weights.items():
        total += scores.get(dim, 0.0) * weight / 10.0
    return round(total, 1)


def create_score_bar_chart(
    extracted_data_list: list[dict],
    weights: dict[str, float],
) -> go.Figure:
    """Horizontal bar chart of weighted overall scores per supplier."""
    names = []
    scores = []
    for data in extracted_data_list:
        dim_scores = _get_scores_from_extracted(data)
        ws = compute_weighted_score(dim_scores, weights)
        names.append(data.get("supplier_name", "Unknown"))
        scores.append(ws)

    max_score = max(scores) if scores else 0
    colors = [CORAL if s == max_score else LIGHT_GRAY for s in scores]

    fig = go.Figure(go.Bar(
        y=names,
        x=scores,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
        textfont=dict(family="Helvetica Neue, Arial, sans-serif", size=13, color=DARK),
    ))

    fig.update_layout(
        xaxis=dict(
            range=[0, 105],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        yaxis=dict(
            autorange="reversed",
            showgrid=False,
        ),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(family="Helvetica Neue, Arial, sans-serif", color=DARK, size=13),
        margin=dict(l=140, r=60, t=20, b=20),
        height=max(160, 70 * len(names)),
    )
    return fig


def generate_pdf_report(
    comparison_data: dict[str, Any],
    extracted_data_list: list[dict[str, Any]],
    weights: dict[str, float],
    scenario_name: str,
) -> bytes:
    """Generate a PDF report of the comparative analysis."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    # Sanitize scenario name for PDF
    safe_scenario = _sanitize_for_pdf(scenario_name)

    # --- Reusable helpers ---

    def _section_header(title: str):
        if pdf.get_y() > pdf.h - 40:
            pdf.add_page()
        pdf.ln(8)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(255, 90, 95)
        pdf.cell(0, 10, _sanitize_for_pdf(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(235, 235, 235)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(72, 72, 72)
        pdf.set_font("Helvetica", "", 10)

    def _sub_header(title: str):
        if pdf.get_y() > pdf.h - 35:
            pdf.add_page()
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(72, 72, 72)
        pdf.cell(0, 7, _sanitize_for_pdf(title), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)

    def _safe_text(text: Any, fallback: str = "N/A") -> str:
        if text is None:
            return fallback
        return _sanitize_for_pdf(str(text))

    def _safe_multi_cell(w, h, txt):
        """Write multi_cell, adding a page if near the bottom."""
        txt = _sanitize_for_pdf(str(txt)).strip()
        if not txt:
            return
        if pdf.get_y() > pdf.h - 35:
            pdf.add_page()
        try:
            pdf.multi_cell(w, h, txt)
        except Exception:
            # If rendering fails, try on a fresh page
            pdf.add_page()
            try:
                pdf.multi_cell(w, h, txt)
            except Exception:
                pass  # Skip un-renderable text

    def _format_value(value: Any) -> str:
        """Format a value from extracted terms for display."""
        if value is None:
            return "Not specified"
        if isinstance(value, list):
            if not value:
                return "None listed"
            return "; ".join(_sanitize_for_pdf(str(v)) for v in value)
        return _sanitize_for_pdf(str(value))

    # --- Cover page ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(255, 90, 95)
    pdf.ln(40)
    pdf.cell(0, 14, "Supplier Proposal Analysis", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(72, 72, 72)
    pdf.cell(0, 10, safe_scenario, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(118, 118, 118)
    pdf.cell(0, 8, f"Generated: {datetime.date.today().strftime('%B %d, %Y')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 8, "AI-Powered Sourcing Intelligence Tool", new_x="LMARGIN", new_y="NEXT", align="C")

    # --- Table of Contents ---
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(72, 72, 72)
    for toc_item in [
        "1. Executive Summary & Recommendation",
        "2. Scoring Summary",
        "3. Score Breakdown by Dimension",
        "4. Extracted Terms Comparison",
        "5. Comparative Highlights",
        "6. Risk Flags",
        "7. Negotiation Strategy",
        "8. Clarification Questions",
        "9. Stress Test",
    ]:
        pdf.cell(0, 8, toc_item, new_x="LMARGIN", new_y="NEXT", align="C")

    # --- 1. Executive Summary ---
    pdf.add_page()
    _section_header("1. Executive Summary & Recommendation")
    _safe_multi_cell(0, 5, _safe_text(comparison_data.get("executive_summary")))
    pdf.ln(6)

    rec = _safe_text(comparison_data.get("recommended_supplier"), "N/A")
    conf = _safe_text(comparison_data.get("confidence_level"), "N/A")
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 90, 95)
    pdf.cell(0, 8, f"Recommended Supplier: {rec}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(72, 72, 72)
    pdf.cell(0, 7, f"Confidence Level: {conf.upper()}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(3)
    _safe_multi_cell(0, 5, _safe_text(comparison_data.get("recommendation_rationale")))

    # --- 2. Scoring Summary ---
    _section_header("2. Scoring Summary")
    dim_labels = {
        "tco_budget_fit": "TCO",
        "pricing_vs_benchmark": "Bench",
        "risk_profile": "Risk",
        "integration_readiness": "Integ",
        "operational_reliability": "Ops",
        "strategic_optionality": "Optn",
        "esg_diversity": "ESG",
    }
    # Use available page width for columns
    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    num_dims = len(dim_labels)
    col_w_total = 22
    col_w_dim = 17
    col_w_name = usable_w - (num_dims * col_w_dim) - col_w_total

    # Header row
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(247, 247, 247)
    pdf.cell(col_w_name, 7, "Supplier", border=1, fill=True)
    for dim_key in dim_labels:
        pdf.cell(col_w_dim, 7, dim_labels[dim_key], border=1, align="C", fill=True)
    pdf.cell(col_w_total, 7, "Weighted", border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)

    # Find best weighted score for highlighting
    all_ws = []
    for data in extracted_data_list:
        s = _get_scores_from_extracted(data)
        all_ws.append(compute_weighted_score(s, weights))
    best_ws = max(all_ws) if all_ws else 0

    for idx, data in enumerate(extracted_data_list):
        s = _get_scores_from_extracted(data)
        ws = compute_weighted_score(s, weights)
        name = _sanitize_for_pdf(data.get("supplier_name", "?"))
        if len(name) > 24:
            name = name[:23] + "."

        # Highlight the best row
        if ws == best_ws:
            pdf.set_fill_color(255, 240, 240)
            fill = True
        else:
            fill = False

        pdf.cell(col_w_name, 7, name, border=1, fill=fill)
        for dim_key in dim_labels:
            pdf.cell(col_w_dim, 7, str(s.get(dim_key, 0)), border=1, align="C", fill=fill)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_w_total, 7, f"{ws:.1f}", border=1, align="C", fill=fill)
        pdf.set_font("Helvetica", "", 9)
        pdf.ln()

    # Weights reference
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(118, 118, 118)
    weight_strs = [f"{DIMENSION_LABELS.get(k, k)}: {v}%" for k, v in weights.items()]
    pdf.cell(0, 5, f"Weights: {', '.join(weight_strs)}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(72, 72, 72)

    # --- 3. Score Breakdown by Dimension ---
    _section_header("3. Score Breakdown by Dimension")
    for dim_key, dim_label in DIMENSION_LABELS.items():
        _sub_header(dim_label)
        for data in extracted_data_list:
            supplier = _safe_text(data.get("supplier_name", "Unknown"))
            s = _get_scores_from_extracted(data)
            score_val = s.get(dim_key, 0)
            rationale = _safe_text(
                data.get("scores", {}).get(dim_key, {}).get("rationale", ""),
                fallback="No rationale provided",
            )
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, f"{supplier}: {score_val}/10", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(118, 118, 118)
            _safe_multi_cell(0, 4, f"  {rationale}")
            pdf.set_text_color(72, 72, 72)
            pdf.ln(2)

    # --- 4. Extracted Terms Comparison ---
    _section_header("4. Extracted Terms Comparison")

    term_categories = {
        "Pricing": "pricing",
        "Scope & Deliverables": "scope_and_deliverables",
        "Service Levels": "service_levels",
        "Risk Factors": "risk_factors",
        "Contract Flexibility": "contract_flexibility",
        "ESG & Diversity": "esg_and_diversity",
    }

    for cat_label, cat_key in term_categories.items():
        _sub_header(cat_label)
        for data in extracted_data_list:
            supplier = _safe_text(data.get("supplier_name", "Unknown"))
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(255, 90, 95)
            pdf.cell(0, 6, supplier, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(72, 72, 72)
            pdf.set_font("Helvetica", "", 8)

            terms = data.get("extracted_terms", {}).get(cat_key, {})
            if isinstance(terms, dict):
                for field, value in terms.items():
                    label = field.replace("_", " ").title()
                    formatted = _format_value(value)
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.cell(50, 4, f"{label}:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "", 8)
                    _safe_multi_cell(0, 4, formatted)
                    pdf.ln(1)
            pdf.ln(3)

    # --- 5. Comparative Highlights ---
    _section_header("5. Comparative Highlights")
    highlights = comparison_data.get("comparative_highlights", [])
    if highlights:
        for h in highlights:
            leader = _safe_text(h.get("leader", ""))
            dimension = _safe_text(h.get("dimension", ""))
            insight = _safe_text(h.get("insight", ""))
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"{dimension} -- Leader: {leader}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            _safe_multi_cell(0, 5, f"  {insight}")
            pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "No comparative highlights available.", new_x="LMARGIN", new_y="NEXT")

    # --- 6. Risk Flags ---
    _section_header("6. Risk Flags")
    has_flags = False
    for data in extracted_data_list:
        supplier = _safe_text(data.get("supplier_name", "Unknown"))
        flags = data.get("risk_flags", [])
        if flags:
            has_flags = True
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, supplier, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for flag in flags:
                sev = _safe_text(flag.get("severity", "")).upper()
                desc = _safe_text(flag.get("description"))
                _safe_multi_cell(0, 5, f"  [{sev}] {desc}")
                pdf.ln(1)
            pdf.ln(3)

    # Top risks from comparison
    top_risks = comparison_data.get("top_risks", [])
    if top_risks:
        _sub_header("Top Risks Across All Suppliers")
        for idx, risk in enumerate(top_risks, 1):
            affected = ", ".join(_safe_text(s) for s in risk.get("affected_suppliers", []))
            risk_desc = _safe_text(risk.get("risk", ""))
            mitigation = _safe_text(risk.get("mitigation", ""))
            pdf.set_font("Helvetica", "B", 9)
            _safe_multi_cell(0, 5, f"  {idx}. {risk_desc}")
            pdf.set_font("Helvetica", "", 8)
            _safe_multi_cell(0, 4, f"     Mitigation: {mitigation}")
            _safe_multi_cell(0, 4, f"     Affects: {affected}")
            pdf.ln(2)

    if not has_flags and not top_risks:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "No risk flags identified.", new_x="LMARGIN", new_y="NEXT")

    # --- 7. Negotiation Strategy ---
    _section_header("7. Negotiation Strategy")
    strategy = comparison_data.get("negotiation_strategy", {})
    for supplier_block in strategy.get("per_supplier", []):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, _safe_text(supplier_block.get("supplier_name")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for lp in supplier_block.get("leverage_points", []):
            point = _safe_text(lp.get("point"))
            ask = _safe_text(lp.get("concrete_ask"))
            impact = _safe_text(lp.get("expected_impact"))
            pdf.set_font("Helvetica", "B", 9)
            _safe_multi_cell(0, 5, f"  * {point}")
            pdf.set_font("Helvetica", "", 8)
            _safe_multi_cell(0, 4, f"    Concrete Ask: {ask}")
            _safe_multi_cell(0, 4, f"    Expected Impact: {impact}")
            pdf.ln(2)
        pdf.ln(3)

    tactics = strategy.get("general_tactics", [])
    if tactics:
        _sub_header("General Negotiation Tactics")
        pdf.set_font("Helvetica", "", 9)
        for t in tactics:
            _safe_multi_cell(0, 5, f"  - {_safe_text(t)}")
            pdf.ln(1)

    # --- 8. Clarification Questions ---
    _section_header("8. Clarification Questions")
    questions = comparison_data.get("clarification_questions", [])
    if questions:
        for idx, q in enumerate(questions, 1):
            directed = _safe_text(q.get("directed_to"))
            question = _safe_text(q.get("question"))
            why = _safe_text(q.get("why_it_matters"))
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, f"{idx}. To: {directed}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            _safe_multi_cell(0, 5, f"  Q: {question}")
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(118, 118, 118)
            _safe_multi_cell(0, 4, f"  Why it matters: {why}")
            pdf.set_text_color(72, 72, 72)
            pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "No clarification questions generated.", new_x="LMARGIN", new_y="NEXT")

    # --- 9. Stress Test ---
    _section_header("9. Stress Test")
    stress = comparison_data.get("stress_test", {})
    wrong_items = stress.get("what_could_go_wrong", [])
    if wrong_items:
        _sub_header("What Could Go Wrong")
        pdf.set_font("Helvetica", "", 9)
        for item in wrong_items:
            _safe_multi_cell(0, 5, f"  - {_safe_text(item)}")
            pdf.ln(1)

    contingency = stress.get("contingency_recommendation")
    if contingency:
        pdf.ln(3)
        _sub_header("Contingency Recommendation")
        pdf.set_font("Helvetica", "", 9)
        _safe_multi_cell(0, 5, f"  {_safe_text(contingency)}")

    # --- Methodology footer ---
    pdf.ln(10)
    pdf.set_draw_color(235, 235, 235)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(118, 118, 118)
    _safe_multi_cell(
        0, 4,
        "This report was generated using AI-assisted multi-criteria evaluation. "
        "All scores, recommendations, and negotiation points should be validated "
        "by sourcing professionals before making contractual commitments. "
        "Final decisions should consider strategic context, relationship history, "
        "and factors beyond this quantitative assessment."
    )

    return bytes(pdf.output())


# Re-export dimension labels for convenience
DIMENSION_LABELS_DISPLAY = DIMENSION_LABELS
