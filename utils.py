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

SUPPLIER_COLORS = [CORAL, TEAL, DARK]
SUPPLIER_FILL_COLORS = [
    "rgba(255,90,95,0.15)",
    "rgba(0,166,153,0.15)",
    "rgba(72,72,72,0.15)",
]

DIMENSION_LABELS = {
    "cost_competitiveness": "Cost Competitiveness",
    "scope_quality": "Scope & Quality",
    "service_reliability": "Service Reliability",
    "risk_profile": "Risk Profile",
    "flexibility": "Flexibility",
    "esg_alignment": "ESG Alignment",
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


def create_radar_chart(
    extracted_data_list: list[dict],
    weights: dict[str, float],
) -> go.Figure:
    """Create a radar/spider chart comparing supplier scores."""
    dimensions = list(DIMENSION_LABELS.keys())
    labels = [DIMENSION_LABELS[d] for d in dimensions]

    fig = go.Figure()

    for i, data in enumerate(extracted_data_list):
        scores = _get_scores_from_extracted(data)
        values = [scores.get(d, 0) for d in dimensions]
        # Close the polygon
        values_closed = values + [values[0]]
        labels_closed = labels + [labels[0]]

        color = SUPPLIER_COLORS[i % len(SUPPLIER_COLORS)]
        fill_color = SUPPLIER_FILL_COLORS[i % len(SUPPLIER_FILL_COLORS)]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            name=data.get("supplier_name", f"Supplier {i + 1}"),
            line=dict(color=color, width=2),
            fill="toself",
            fillcolor=fill_color,
        ))

    fig.update_layout(
        polar=dict(
            bgcolor=WHITE,
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickvals=[2, 4, 6, 8, 10],
                gridcolor="#EBEBEB",
                linecolor="#EBEBEB",
            ),
            angularaxis=dict(
                gridcolor="#EBEBEB",
                linecolor="#EBEBEB",
            ),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(family="Helvetica Neue, Arial, sans-serif", size=12, color=DARK),
        ),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(family="Helvetica Neue, Arial, sans-serif", color=DARK),
        margin=dict(l=60, r=60, t=30, b=60),
        height=420,
    )
    return fig


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
    pdf.set_auto_page_break(auto=True, margin=20)

    # Sanitize scenario name for PDF
    safe_scenario = _sanitize_for_pdf(scenario_name)

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

    def _section_header(title: str):
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(255, 90, 95)
        pdf.cell(0, 10, _sanitize_for_pdf(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(235, 235, 235)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(72, 72, 72)
        pdf.set_font("Helvetica", "", 10)

    def _safe_text(text: Any, fallback: str = "N/A") -> str:
        if text is None:
            return fallback
        return _sanitize_for_pdf(str(text))

    def _safe_multi_cell(w, h, txt):
        """Write multi_cell, adding a page if near the bottom."""
        txt = _sanitize_for_pdf(str(txt))
        if pdf.get_y() > pdf.h - 30:
            pdf.add_page()
        try:
            pdf.multi_cell(w, h, txt)
        except Exception:
            pdf.add_page()
            try:
                pdf.multi_cell(w, h, txt)
            except Exception:
                pass  # Skip text that still can't render

    # --- Executive Summary ---
    pdf.add_page()
    _section_header("Executive Summary")
    _safe_multi_cell(0, 5, _safe_text(comparison_data.get("executive_summary")))
    pdf.ln(4)

    rec = _safe_text(comparison_data.get("recommended_supplier"), "N/A")
    conf = _safe_text(comparison_data.get("confidence_level"), "N/A")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Recommended Supplier: {rec}  |  Confidence: {conf.upper()}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(2)
    _safe_multi_cell(0, 5, _safe_text(comparison_data.get("recommendation_rationale")))

    # --- Scoring Summary ---
    _section_header("Scoring Summary")
    dim_labels = {
        "cost_competitiveness": "Cost",
        "scope_quality": "Scope",
        "service_reliability": "Reliability",
        "risk_profile": "Risk",
        "flexibility": "Flexibility",
        "esg_alignment": "ESG",
    }
    # Header row
    pdf.set_font("Helvetica", "B", 9)
    col_w_name = 38
    col_w_dim = 18
    col_w_total = 22
    pdf.cell(col_w_name, 6, "Supplier", border=1)
    for dim_key in dim_labels:
        pdf.cell(col_w_dim, 6, dim_labels[dim_key], border=1, align="C")
    pdf.cell(col_w_total, 6, "Weighted", border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)

    for data in extracted_data_list:
        s = _get_scores_from_extracted(data)
        ws = compute_weighted_score(s, weights)
        name = _sanitize_for_pdf(data.get("supplier_name", "?"))
        if len(name) > 18:
            name = name[:17] + "."
        pdf.cell(col_w_name, 6, name, border=1)
        for dim_key in dim_labels:
            pdf.cell(col_w_dim, 6, str(s.get(dim_key, 0)), border=1, align="C")
        pdf.cell(col_w_total, 6, f"{ws:.1f}", border=1, align="C")
        pdf.ln()

    # --- Risk Flags ---
    _section_header("Risk Flags")
    for data in extracted_data_list:
        supplier = data.get("supplier_name", "Unknown")
        flags = data.get("risk_flags", [])
        if flags:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, supplier, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for flag in flags:
                sev = _safe_text(flag.get("severity", "")).upper()
                desc = _safe_text(flag.get("description"))
                _safe_multi_cell(0, 5, f"  [{sev}] {desc}")
            pdf.ln(2)

    # --- Negotiation Strategy ---
    _section_header("Negotiation Strategy")
    strategy = comparison_data.get("negotiation_strategy", {})
    for supplier_block in strategy.get("per_supplier", []):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, _safe_text(supplier_block.get("supplier_name")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for lp in supplier_block.get("leverage_points", []):
            point = _safe_text(lp.get("point"))
            ask = _safe_text(lp.get("concrete_ask"))
            impact = _safe_text(lp.get("expected_impact"))
            _safe_multi_cell(0, 5, f"  * {point}")
            _safe_multi_cell(0, 5, f"    Ask: {ask}")
            _safe_multi_cell(0, 5, f"    Impact: {impact}")
            pdf.ln(1)
        pdf.ln(2)

    tactics = strategy.get("general_tactics", [])
    if tactics:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "General Tactics", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for t in tactics:
            _safe_multi_cell(0, 5, f"  - {_safe_text(t)}")

    # --- Clarification Questions ---
    _section_header("Clarification Questions")
    for q in comparison_data.get("clarification_questions", []):
        pdf.set_font("Helvetica", "B", 9)
        directed = _safe_text(q.get("directed_to"))
        pdf.cell(0, 5, f"To: {directed}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        _safe_multi_cell(0, 5, f"  Q: {_safe_text(q.get('question'))}")
        _safe_multi_cell(0, 5, f"  Why: {_safe_text(q.get('why_it_matters'))}")
        pdf.ln(2)

    # --- Stress Test ---
    _section_header("Stress Test")
    stress = comparison_data.get("stress_test", {})
    for item in stress.get("what_could_go_wrong", []):
        _safe_multi_cell(0, 5, f"  - {_safe_text(item)}")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Contingency:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    _safe_multi_cell(0, 5, f"  {_safe_text(stress.get('contingency_recommendation'))}")

    # --- Methodology footer ---
    pdf.ln(8)
    pdf.set_draw_color(235, 235, 235)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(118, 118, 118)
    weight_strs = [f"{DIMENSION_LABELS.get(k, k)}: {v}%" for k, v in weights.items()]
    _safe_multi_cell(
        0, 4,
        "AI-assisted analysis using weighted multi-criteria evaluation. "
        f"Weights used: {', '.join(weight_strs)}. "
        "This analysis should be validated by sourcing professionals before "
        "making contractual commitments."
    )

    return bytes(pdf.output())


# Re-export dimension labels for convenience
DIMENSION_LABELS_DISPLAY = DIMENSION_LABELS
