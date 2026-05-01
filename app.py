"""Proposal Comparison Engine -- Main Streamlit application."""

from __future__ import annotations

import datetime
import json
import pathlib
import re

import pandas as pd
import streamlit as st

from airbnb_context import AIRBNB_CONTEXT
from findings_engine import run_all_findings
from prompts import (
    COMPARE_SCHEMA,
    EXTRACT_SCHEMA,
    build_context_block,
    get_compare_prompt,
    get_extract_prompt,
)
from sample_data import SAMPLE_PROPOSALS
from utils import (
    DIMENSION_LABELS,
    _get_scores_from_extracted,
    compute_weighted_score,
    create_score_bar_chart,
    generate_pdf_report,
    parse_pdf,
)


# ── Adapter: structured_data (sample_data schema) -> findings_engine schema ─
# The findings engine expects a flat supplier dict (net_price, support_pct,
# uptime_sla_pct, ...). The new sample_data carries a tiered structured_data
# dict. This adapter bridges them for the engine.

_CONTRACT_FY = ("FY-2025", "FY-2026", "FY-2027")


def _tier_index_for_seats(seats: int) -> int:
    """Return tier index 0/1/2 matching ['0-1K', '1K-5K', '5K+']."""
    if seats <= 1000:
        return 0
    if seats < 5000:
        return 1
    return 2


def _parse_termination_penalty(formula: str) -> dict:
    """Parse a plain-language termination penalty into engine penalty dict."""
    text = (formula or "").lower()
    if "no fee" in text or "no penalty" in text:
        return {"type": "none", "value": 0}
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*remaining\s*tcv", text)
    if m:
        return {"type": "pct_of_remaining_tcv", "value": float(m.group(1))}
    m2 = re.search(r"\$([\d,]+)", text)
    if m2:
        return {"type": "fixed", "value": float(m2.group(1).replace(",", ""))}
    return {"type": "none", "value": 0}


def adapt_structured_for_engine(supplier_name: str, sd: dict) -> dict:
    """Convert sample_data structured_data dict into findings_engine input.

    Computes a seat-weighted average net_price across the contract term so
    the engine's flat-price 3-year TCO total matches the tier-aware reality.
    """
    tier_net_price = sd.get("tier_net_price") or [0, 0, 0]
    total_seats = 0
    weighted_sum = 0.0
    for fy in _CONTRACT_FY:
        seats = next(
            (u.expected_seats for u in AIRBNB_CONTEXT.usage if u.fiscal_year == fy),
            0,
        )
        idx = _tier_index_for_seats(seats)
        if 0 <= idx < len(tier_net_price):
            weighted_sum += tier_net_price[idx] * seats
            total_seats += seats
    representative_price = (
        weighted_sum / total_seats if total_seats else (tier_net_price[1] if len(tier_net_price) > 1 else 0)
    )

    residency_list = sd.get("data_residency", []) or []
    if len(residency_list) == 1:
        residency_str = f"single-region ({residency_list[0]})"
    elif residency_list:
        residency_str = "multi-region (" + ", ".join(residency_list) + ")"
    else:
        residency_str = "unspecified"

    return {
        "supplier_name": supplier_name,
        "net_price": round(representative_price, 2),
        "support_pct": float(sd.get("annual_support_pct", 0)),
        "implementation_fee": float(sd.get("implementation_fee", 0)),
        "uptime_sla_pct": float(sd.get("uptime_sla", 0)),
        "sla_credit_pct": float(sd.get("sla_credit_pct", 0)),
        "termination_notice_days": int(sd.get("termination_notice_days", 0)),
        "termination_penalty": _parse_termination_penalty(
            sd.get("termination_penalty_formula", "")
        ),
        "certs": sd.get("data_privacy_certs", []) or [],
        "data_residency": residency_str,
    }

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Proposal Comparison Engine",
    # page_icon intentionally omitted for enterprise look
    layout="wide",
)

# ── Airbnb Custom CSS ───────────────────────────────────────────────────────
AIRBNB_CSS = """
<style>
/* ── Global ────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: -apple-system, "Cereal", "Helvetica Neue", Helvetica, Arial, sans-serif;
    color: #484848;
    font-size: 14px;
}

/* Captions and small text */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #767676 !important;
    font-size: 12px !important;
    line-height: 1.5;
}

/* Section headers tighter */
.stMarkdown h5 {
    font-size: 15px;
    font-weight: 600;
    color: #222222;
    margin: 16px 0 10px 0 !important;
    letter-spacing: -0.1px;
}

/* App header right-aligned meta label */
.app-header-meta {
    margin-left: auto;
    font-size: 11px;
    color: #767676;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    align-self: center;
}

/* Remove Streamlit top padding */
.block-container { padding-top: 1.5rem !important; max-width: 1200px; }

/* ── Sidebar ───────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #EBEBEB;
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }

/* ── Tabs ──────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #EBEBEB;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #767676;
    font-weight: 500;
    font-size: 14px;
    padding: 12px 20px;
    border-radius: 0 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #484848 !important;
    border-bottom: 2px solid #FF5A5F !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #484848; }
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Primary button ────────────────────────────────────────────── */
.stButton > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button,
.stButton > button[data-testid="stBaseButton-primary"] {
    background-color: #FF5A5F !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.25rem !important;
    transition: background-color 0.2s ease;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background-color: #E00007 !important;
    color: #FFFFFF !important;
}

/* ── Download button ───────────────────────────────────────────── */
.stDownloadButton > button {
    background-color: #FF5A5F !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stDownloadButton > button:hover {
    background-color: #E00007 !important;
    color: #FFFFFF !important;
}

/* ── Metric ────────────────────────────────────────────────────── */
[data-testid="stMetricLabel"] {
    color: #484848 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    color: #222222 !important;
    font-weight: 700 !important;
    font-size: 32px !important;
}
[data-testid="stMetricDelta"] { font-size: 13px !important; }

/* ── Expander ──────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background-color: #F7F7F7;
    border-radius: 12px;
    border: 1px solid #EBEBEB;
    font-weight: 500;
    color: #484848;
}
details[data-testid="stExpander"] {
    background-color: #F7F7F7;
    border: 1px solid #EBEBEB;
    border-radius: 12px;
    overflow: hidden;
}
details[data-testid="stExpander"] summary {
    background-color: #F7F7F7;
    padding: 12px 16px;
}

/* ── Tables / dataframe ────────────────────────────────────────── */
.stDataFrame thead th {
    background-color: #F7F7F7 !important;
    border-color: #EBEBEB !important;
    color: #484848 !important;
    font-weight: 600;
}
.stDataFrame td { border-color: #EBEBEB !important; }

/* ── Card style ────────────────────────────────────────────────── */
.airbnb-card {
    background: #FFFFFF;
    border: 1px solid #EBEBEB;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
.airbnb-card-coral {
    background: #FFFFFF;
    border: 1px solid #EBEBEB;
    border-left: 3px solid #FF5A5F;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
.airbnb-card-amber {
    background: #FFFFFF;
    border: 1px solid #EBEBEB;
    border-left: 3px solid #FFB400;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
.airbnb-card-highlight {
    background: #FFFFFF;
    border: 2px solid #FF5A5F;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(255,90,95,0.12);
    margin-bottom: 16px;
}

/* ── Badges ────────────────────────────────────────────────────── */
.badge-coral {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    background: #FFF0F0; color: #FF5A5F; font-size: 12px; font-weight: 600;
}
.badge-teal {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    background: #E6F7F5; color: #00A699; font-size: 12px; font-weight: 600;
}
.badge-green {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    background: #E6F7E6; color: #008A00; font-size: 12px; font-weight: 600;
}
.badge-amber {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    background: #FFF5E0; color: #B8860B; font-size: 12px; font-weight: 600;
}
.badge-red {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    background: #FFF0F0; color: #D93025; font-size: 12px; font-weight: 600;
}

/* ── Misc ──────────────────────────────────────────────────────── */
.divider { border: none; border-top: 1px solid #F0F0F0; margin: 24px 0; }

/* Slider coral accent */
.stSlider [data-testid="stThumbValue"] { color: #FF5A5F; }
.stSlider [role="slider"] { background-color: #FF5A5F !important; }
div[data-baseweb="slider"] div[role="progressbar"] > div {
    background-color: #FF5A5F !important;
}

/* Status steps cleaner */
[data-testid="stStatusWidget"] { border-radius: 12px; }

/* Text input / text area */
.stTextInput input, .stTextArea textarea {
    border-radius: 8px !important;
    border-color: #EBEBEB !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #FF5A5F !important;
    box-shadow: 0 0 0 1px #FF5A5F !important;
}

/* Radio buttons horizontal */
.stRadio > div { gap: 12px; }

/* Placeholder text style */
.placeholder-text {
    text-align: center; color: #767676; padding: 60px 20px; font-size: 15px;
}

/* Logo sizing */
.airbnb-logo svg { width: 120px; height: 40px; }

/* Compact header bar */
.app-header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 8px 0 12px 0;
}
.app-header svg { width: auto; height: 30px; flex-shrink: 0; }
.app-header-text { display: flex; flex-direction: column; }
.app-header-title {
    font-size: 20px; font-weight: 600; color: #222222;
    line-height: 1.2; margin: 0;
}
.app-header-sub {
    font-size: 13px; color: #767676; margin: 2px 0 0 0;
    line-height: 1.3;
}

/* Success banner animation */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
}
.success-banner {
    animation: fadeInDown 0.4s ease;
    background: #E6F7F5;
    border: 1px solid #00A699;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
    color: #00A699;
    font-weight: 500;
    font-size: 14px;
}

/* Toggle coral accent */
.stToggle label span[data-testid="stToggleLabel"] { color: #484848; }
</style>
"""
st.markdown(AIRBNB_CSS, unsafe_allow_html=True)


# ── Helper: escape dollar signs for Streamlit markdown (prevent LaTeX) ─────
def _esc(text) -> str:
    """Escape $ signs so Streamlit doesn't render them as LaTeX math."""
    return str(text).replace("$", "\\$") if text else ""


# ── Helper: render card ─────────────────────────────────────────────────────
def render_card(content_html: str, variant: str = "default"):
    """Render all card content in a single st.markdown call so the div actually wraps it."""
    cls = {
        "coral": "airbnb-card-coral",
        "amber": "airbnb-card-amber",
        "highlight": "airbnb-card-highlight",
    }.get(variant, "airbnb-card")
    st.markdown(f'<div class="{cls}">{content_html}</div>', unsafe_allow_html=True)


# ── Helper: parse Claude JSON ──────────────────────────────────────────────
def _parse_json_response(text: str) -> dict | None:
    """Try to extract a JSON object from Claude's response text."""
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first { and last }
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            return json.loads(cleaned[first : last + 1])
        except json.JSONDecodeError:
            pass

    return None


# ── Helper: call Claude API ────────────────────────────────────────────────
def call_claude(
    client,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 2,
) -> dict | None:
    """Call Claude and return parsed JSON dict, with retries on parse failure."""
    import anthropic

    for attempt in range(max_retries):
        prompt = user_prompt
        if attempt > 0:
            prompt += (
                "\n\nYour previous response was not valid JSON. "
                "Return ONLY the JSON object, no markdown formatting or backticks."
            )
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            last_text = response.content[0].text
            result = _parse_json_response(last_text)
            if result is not None:
                return result
        except anthropic.APIError as e:
            st.error(f"API error: {e}")
            return None
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return None

    st.error("Failed to get valid JSON from Claude after retries.")
    return None


# ── Helper: safe get for nested dicts ──────────────────────────────────────
def _safe(data: dict | None, *keys, default="N/A"):
    """Safely traverse nested dict keys."""
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
    if current is None:
        return default
    return current


# ── Session state defaults ─────────────────────────────────────────────────
st.session_state.setdefault("use_sample", False)
st.session_state.setdefault("num_suppliers", 2)
st.session_state.setdefault("extracted_data", [])
st.session_state.setdefault("comparison_data", None)
st.session_state.setdefault("pdf_report", None)
st.session_state.setdefault("analysis_done", False)
st.session_state.setdefault("just_analyzed", False)
st.session_state.setdefault("findings_per_supplier", [])
st.session_state.setdefault("w_tco", 25)
st.session_state.setdefault("w_bench", 15)
st.session_state.setdefault("w_risk", 20)
st.session_state.setdefault("w_integ", 20)
st.session_state.setdefault("w_ops", 10)
st.session_state.setdefault("w_optionality", 5)
st.session_state.setdefault("w_esg", 5)

# Supplier inputs
for _i in range(3):
    st.session_state.setdefault(f"supplier_{_i}_name", "")
    st.session_state.setdefault(f"supplier_{_i}_text", "")
    st.session_state.setdefault(f"supplier_{_i}_method", "Paste text")


# ── Page header ─────────────────────────────────────────────────────────────
ASSETS_DIR = pathlib.Path(__file__).parent / "assets"
logo_path = ASSETS_DIR / "airbnb_logo.svg"
logo_svg = logo_path.read_text() if logo_path.exists() else ""

st.markdown(
    f'<div class="app-header">'
    f'{logo_svg}'
    f'<div class="app-header-text">'
    f'<p class="app-header-title">Sourcing Decision Engine &mdash; Data &amp; Analytics Renewal</p>'
    f'<p class="app-header-sub">AI-augmented analysis grounded in Airbnb sourcing context</p>'
    f'</div>'
    f'<div class="app-header-meta">Internal demo &middot; Sourcing Operations &amp; Innovation</div>'
    f'</div>'
    f'<hr class="divider">',
    unsafe_allow_html=True,
)

# Static analysis-complete notice (no animation)
if st.session_state.get("just_analyzed"):
    st.markdown(
        '<p style="color:#00A699;font-size:13px;margin:4px 0 16px 0;">'
        "Analysis complete. View results in the Comparison Matrix or "
        "Negotiation Brief tabs."
        "</p>",
        unsafe_allow_html=True,
    )
    st.session_state["just_analyzed"] = False

# (Where-this-fits expander removed for enterprise demo polish.)


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    # Sample data toggle
    use_sample = st.toggle("Load sample scenario", key="use_sample")
    if use_sample:
        st.info(
            f"Loaded: {SAMPLE_PROPOSALS['scenario_name']} with "
            f"{len(SAMPLE_PROPOSALS['proposals'])} suppliers"
        )
        # Populate supplier inputs
        for i, p in enumerate(SAMPLE_PROPOSALS["proposals"]):
            st.session_state[f"supplier_{i}_name"] = p["supplier_name"]
            st.session_state[f"supplier_{i}_text"] = p["proposal_text"]
            st.session_state[f"supplier_{i}_method"] = "Paste text"
        st.session_state["num_suppliers"] = len(SAMPLE_PROPOSALS["proposals"])
    else:
        # If toggle was just turned off, clear sample data
        if any(
            st.session_state.get(f"supplier_{i}_name") == p["supplier_name"]
            for i, p in enumerate(SAMPLE_PROPOSALS["proposals"])
        ):
            for i in range(len(SAMPLE_PROPOSALS["proposals"])):
                st.session_state[f"supplier_{i}_name"] = ""
                st.session_state[f"supplier_{i}_text"] = ""
            st.session_state["num_suppliers"] = 2

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Evaluation Criteria Weights
    st.markdown("#### Evaluation Criteria Weights")
    st.caption("Adjust to reflect your sourcing priorities. Must sum to 100%.")

    w_tco = st.slider("TCO & Budget Fit", 0, 50, step=5, key="w_tco")
    w_bench = st.slider("Pricing vs Benchmark", 0, 50, step=5, key="w_bench")
    w_risk = st.slider("Risk Profile", 0, 50, step=5, key="w_risk")
    w_integ = st.slider("Integration Readiness", 0, 50, step=5, key="w_integ")
    w_ops = st.slider("Operational Reliability", 0, 50, step=5, key="w_ops")
    w_optionality = st.slider("Strategic Optionality", 0, 50, step=5, key="w_optionality")
    w_esg = st.slider("ESG & Diversity", 0, 50, step=5, key="w_esg")

    total_weight = w_tco + w_bench + w_risk + w_integ + w_ops + w_optionality + w_esg
    if total_weight != 100:
        st.warning(f"Weights must sum to 100%. Currently: {total_weight}%")
    else:
        st.success("Weights sum to 100%")

    weights = {
        "tco_budget_fit": w_tco,
        "pricing_vs_benchmark": w_bench,
        "risk_profile": w_risk,
        "integration_readiness": w_integ,
        "operational_reliability": w_ops,
        "strategic_optionality": w_optionality,
        "esg_diversity": w_esg,
    }

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Count valid proposals
    valid_proposals = 0
    for i in range(st.session_state["num_suppliers"]):
        name = st.session_state.get(f"supplier_{i}_name", "")
        text = st.session_state.get(f"supplier_{i}_text", "")
        if name.strip() and text.strip():
            valid_proposals += 1

    can_analyze = valid_proposals >= 2 and total_weight == 100


# ── Airbnb Sourcing Context panel (above tabs) ─────────────────────────────
_n_bench = len(AIRBNB_CONTEXT.benchmarks)
_n_usage = len(AIRBNB_CONTEXT.usage)
_n_budget = len(AIRBNB_CONTEXT.budget)
_n_integ = len(AIRBNB_CONTEXT.integrations)

st.markdown(
    f'<p style="font-size:13px;color:#484848;margin:4px 0 8px 0;">'
    f"Airbnb Sourcing Context loaded &mdash; "
    f"{_n_bench} industry benchmarks &middot; "
    f"{_n_usage} fiscal-year forecasts &middot; "
    f"{_n_budget}-year FP&amp;A envelope &middot; "
    f"{_n_integ} integration dependencies"
    f"</p>",
    unsafe_allow_html=True,
)

with st.expander("Airbnb Sourcing Context — Knowledge Base", expanded=False):
    _kb_col_left, _kb_col_right = st.columns(2)

    # --- Industry Benchmarks (top-left) ---
    with _kb_col_left:
        st.markdown("##### Industry benchmarks")
        _bench_df = pd.DataFrame(
            [
                {
                    "Metric": b.metric,
                    "P10": b.p10,
                    "Median": b.median,
                    "P90": b.p90,
                    "Unit": b.unit,
                }
                for b in AIRBNB_CONTEXT.benchmarks
            ]
        )
        st.dataframe(_bench_df, use_container_width=True, hide_index=True)

    # --- Usage Forecast (top-right) ---
    with _kb_col_right:
        st.markdown("##### Usage forecast")
        _usage_df = pd.DataFrame(
            [
                {
                    "FY": u.fiscal_year,
                    "Expected Seats": f"{u.expected_seats:,}",
                    "YoY Growth": (
                        f"{u.yoy_growth_pct:.0f}%" if u.yoy_growth_pct is not None else "—"
                    ),
                    "Notes": u.notes,
                }
                for u in AIRBNB_CONTEXT.usage
            ]
        )
        st.dataframe(_usage_df, use_container_width=True, hide_index=True)

    _kb_col_left2, _kb_col_right2 = st.columns(2)

    # --- FP&A Budget (bottom-left) with editable FY-26 override ---
    with _kb_col_left2:
        st.markdown("##### FP&A budget")
        _budget_df = pd.DataFrame(
            [
                {
                    "FY": e.fiscal_year,
                    "License": f"${e.license_budget:,.0f}",
                    "Implementation": (
                        f"${e.implementation_pool:,.0f}"
                        if e.implementation_pool is not None
                        else "—"
                    ),
                    "Support": f"${e.support_budget:,.0f}",
                }
                for e in AIRBNB_CONTEXT.budget
            ]
        )
        st.dataframe(_budget_df, use_container_width=True, hide_index=True)

        _current_fy26 = next(
            (e.license_budget for e in AIRBNB_CONTEXT.budget if e.fiscal_year == "FY-2026"),
            0.0,
        )
        _new_fy26 = st.number_input(
            "Override FY-26 license budget ($)",
            min_value=0,
            value=int(_current_fy26),
            step=10_000,
            key="override_fy26_license",
        )
        if int(_new_fy26) != int(_current_fy26):
            AIRBNB_CONTEXT.update_budget("FY-2026", float(_new_fy26))
        st.caption(
            "Edits persist for the current session. Adjust to model budget "
            "revisions before re-running analysis."
        )

    # --- Integration Dependencies (bottom-right) ---
    with _kb_col_right2:
        st.markdown("##### Integration dependencies")
        _integ_df = pd.DataFrame(
            [
                {
                    "Dep ID": d.dep_id,
                    "Description": d.description,
                    "Criticality": d.criticality,
                    "Owner": d.owner,
                }
                for d in AIRBNB_CONTEXT.integrations
            ]
        )
        st.dataframe(_integ_df, use_container_width=True, hide_index=True)


# ── Main content — 3 Tabs ──────────────────────────────────────────────────
tab_input, tab_compare, tab_brief = st.tabs(
    ["Input Proposals", "Comparison Matrix", "Negotiation Brief"]
)


# ── TAB 1: Input Proposals ──────────────────────────────────────────────────
with tab_input:
    num = st.session_state["num_suppliers"]

    for i in range(num):
        col_name, col_method = st.columns([3, 2])
        with col_name:
            st.text_input(
                f"Supplier {i + 1} Name",
                placeholder="e.g., Eventide Solutions",
                key=f"supplier_{i}_name",
            )
        with col_method:
            st.radio(
                "Input method",
                ["Paste text", "Upload PDF"],
                horizontal=True,
                key=f"supplier_{i}_method",
                label_visibility="collapsed",
            )

        method = st.session_state.get(f"supplier_{i}_method", "Paste text")
        if method == "Paste text":
            st.text_area(
                f"Proposal text for Supplier {i + 1}",
                height=280,
                placeholder=(
                    "Paste the full supplier proposal here including pricing, "
                    "scope, SLAs, terms, and any relevant sections..."
                ),
                key=f"supplier_{i}_text",
                label_visibility="collapsed",
            )
        else:
            uploaded = st.file_uploader(
                f"Upload proposal for Supplier {i + 1}",
                type=["pdf", "txt"],
                key=f"supplier_{i}_file",
                label_visibility="collapsed",
            )
            if uploaded is not None:
                if uploaded.name.endswith(".pdf"):
                    extracted = parse_pdf(uploaded)
                else:
                    extracted = uploaded.read().decode("utf-8", errors="replace")
                if extracted:
                    st.session_state[f"supplier_{i}_text"] = extracted
                    st.success(f"Extracted {len(extracted):,} characters")
                else:
                    st.error("Could not extract text from the uploaded file.")

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if num < 3:
        if st.button("Add third supplier"):
            st.session_state["num_suppliers"] = 3
            st.rerun()

    # ── Inline CTA ──────────────────────────────────────────────────────
    st.markdown("")  # spacer

    inline_can_analyze = valid_proposals >= 2 and total_weight == 100
    inline_analyze = st.button(
        "Run comparison and generate negotiation brief",
        type="primary",
        use_container_width=True,
        disabled=not inline_can_analyze,
        key="inline_analyze",
    )
    st.markdown(
        '<p style="text-align:center;font-size:12px;color:#767676;margin:6px 0 0 0;">'
        "Uses AI to extract terms, score suppliers, and prepare a negotiation brief. "
        "Human review required before decisions.</p>",
        unsafe_allow_html=True,
    )


# ── TAB 2: Comparison Matrix ────────────────────────────────────────────────
# Helpers used only by Tab 2's deal comparison table -----------------------

_DEAL_TABLE_BG = {"green": "#E6F7F5", "yellow": "#FFF5E0", "red": "#FFF0F0"}
_DEAL_TABLE_FG = {"green": "#00A699", "yellow": "#B8860B", "red": "#D93025"}


def _deal_cell_html(text: str, color):
    """One <td> rendered with a coloured background or plain styling."""
    if color in _DEAL_TABLE_BG:
        bg = _DEAL_TABLE_BG[color]
        fg = _DEAL_TABLE_FG[color]
        style = (
            f"background:{bg};color:{fg};padding:9px 12px;"
            f"border-bottom:1px solid #EBEBEB;font-weight:500;text-align:center;"
        )
    else:
        style = (
            "padding:9px 12px;border-bottom:1px solid #EBEBEB;"
            "color:#484848;text-align:center;"
        )
    return f'<td style="{style}">{text}</td>'


def _build_deal_comparison_table(extracted_list, findings_list, sd_lookup):
    """Build the deterministic-findings-driven comparison table as HTML."""
    median_price = 250.0
    p90_price = 310.0
    median_uptime = 99.9

    cols_html = "".join(
        f'<th style="padding:10px 12px;text-align:center;'
        f"font-weight:600;color:#484848;border-bottom:2px solid #EBEBEB;"
        f'background:#F7F7F7;">{_esc(d.get("supplier_name", f"Supplier {i+1}"))}</th>'
        for i, d in enumerate(extracted_list)
    )
    header = (
        '<tr><th style="padding:10px 12px;text-align:left;font-weight:600;'
        "color:#484848;border-bottom:2px solid #EBEBEB;background:#F7F7F7;"
        'min-width:220px;">Metric</th>'
        f"{cols_html}</tr>"
    )

    rows = []

    def _row(label, cells):
        cell_html = "".join(_deal_cell_html(t, c) for t, c in cells)
        return (
            '<tr><td style="padding:9px 12px;border-bottom:1px solid #EBEBEB;'
            f'color:#484848;font-weight:500;">{label}</td>{cell_html}</tr>'
        )

    # Row 1: 3-Year TCO (informational)
    tco_cells = []
    for fnd in findings_list:
        tco_total = (fnd.get("tco") or {}).get("total_3yr_tco", 0)
        tco_cells.append((f"${tco_total / 1_000_000:.2f}M", None))
    rows.append(_row("3-year TCO", tco_cells))

    # Row 2: % of 3-Year Budget Envelope
    budget_cells = []
    for fnd in findings_list:
        budget = fnd.get("budget") or {}
        req = budget.get("total_3yr_required", 0)
        avail = budget.get("total_3yr_available", 0)
        if avail > 0:
            pct = req / avail * 100
            if pct <= 95:
                color = "green"
            elif pct <= 105:
                color = "yellow"
            else:
                color = "red"
            budget_cells.append((f"{pct:.0f}% of envelope", color))
        else:
            budget_cells.append(("—", None))
    rows.append(_row("% of 3-year budget envelope", budget_cells))

    # Row 3: Net Price (1K-5K) vs Median
    price_cells = []
    for fnd in findings_list:
        name = fnd.get("supplier_name", "")
        sd = sd_lookup.get(name) or {}
        tier_prices = sd.get("tier_net_price") or []
        if len(tier_prices) >= 2:
            price = tier_prices[1]
            delta = price - median_price
            sign = "+" if delta >= 0 else "-"
            if price <= median_price:
                color = "green"
            elif price <= p90_price:
                color = "yellow"
            else:
                color = "red"
            price_cells.append(
                (f"${price:.0f} ({sign}${abs(delta):.0f} vs median)", color)
            )
        else:
            price_cells.append(("—", None))
    rows.append(_row("Net price (1K-5K) vs median", price_cells))

    # Row 4: Uptime SLA vs Median
    uptime_cells = []
    for fnd in findings_list:
        name = fnd.get("supplier_name", "")
        sd = sd_lookup.get(name) or {}
        uptime = sd.get("uptime_sla")
        if uptime is None:
            for b in fnd.get("benchmarks", []):
                if b.get("metric") == "Uptime SLA":
                    uptime = b.get("supplier_value")
                    break
        if uptime is None:
            uptime_cells.append(("—", None))
        else:
            color = "green" if uptime >= median_uptime else "red"
            uptime_cells.append((f"{uptime:.2f}%", color))
    rows.append(_row("Uptime SLA vs median", uptime_cells))

    # Row 5: Termination Cost @ End of Y1 (informational)
    exit_cells = []
    for fnd in findings_list:
        cost = fnd.get("exit_cost", 0) or 0
        if cost == 0:
            label = "$0"
        elif cost < 1_000_000:
            label = f"${cost / 1000:.0f}K"
        else:
            label = f"${cost / 1_000_000:.2f}M"
        exit_cells.append((label, None))
    rows.append(_row("Termination cost at end of Y1", exit_cells))

    # Row 6: Compliance & Residency
    comp_cells = []
    for fnd in findings_list:
        name = fnd.get("supplier_name", "")
        sd = sd_lookup.get(name) or {}
        certs = sd.get("data_privacy_certs") or []
        residency = sd.get("data_residency") or []
        has_type_ii = any("type ii" in str(c).lower() for c in certs)
        n_regions = len(residency)
        is_multi = n_regions >= 2
        if has_type_ii and is_multi:
            color = "green"
        elif (not has_type_ii) and (not is_multi):
            color = "red"
        else:
            color = "yellow"
        cert_label = "SOC 2 Type II" if has_type_ii else "no Type II"
        region_label = f"{n_regions} region" + ("s" if n_regions != 1 else "")
        comp_cells.append((f"{cert_label} + {region_label}", color))
    rows.append(_row("Compliance and residency", comp_cells))

    # Row 7: Integration Coverage
    integ_cells = []
    total = len(AIRBNB_CONTEXT.integrations)
    for fnd in findings_list:
        integ = fnd.get("integration") or []
        covered = len(integ)
        if total == 0:
            integ_cells.append(("—", None))
        else:
            if covered >= 4:
                color = "green"
            elif covered >= 2:
                color = "yellow"
            else:
                color = "red"
            integ_cells.append((f"{covered} of {total}", color))
    rows.append(_row("Integration coverage", integ_cells))

    rows_html = "".join(rows)
    return (
        '<table style="width:100%;border-collapse:collapse;background:#FFFFFF;'
        "border:1px solid #EBEBEB;border-radius:12px;overflow:hidden;"
        'font-family:Helvetica Neue, Arial, sans-serif;font-size:13px;">'
        f"<thead>{header}</thead><tbody>{rows_html}</tbody></table>"
    )


with tab_compare:
    if not st.session_state.get("analysis_done"):
        st.markdown(
            '<div class="placeholder-text">'
            "<p>Run an analysis to see the comparison matrix.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        extracted_list = st.session_state["extracted_data"]
        comparison = st.session_state["comparison_data"]
        findings_list = st.session_state.get("findings_per_supplier", []) or []
        sd_lookup = {
            p["supplier_name"]: p.get("structured_data")
            for p in SAMPLE_PROPOSALS.get("proposals", [])
        }

        # 1. Headline Score Cards
        st.markdown("##### Overall weighted scores")
        all_scores = []
        for data in extracted_list:
            s = _get_scores_from_extracted(data)
            ws = compute_weighted_score(s, weights)
            all_scores.append(ws)

        max_ws = max(all_scores) if all_scores else 0
        cols = st.columns(len(extracted_list))
        for idx, (data, ws) in enumerate(zip(extracted_list, all_scores)):
            with cols[idx]:
                name = data.get("supplier_name", f"Supplier {idx + 1}")
                delta = f"{ws - max_ws:+.1f}" if ws != max_ws else "Highest"
                is_top = ws == max_ws
                delta_color = "#00A699" if is_top else "#767676"
                render_card(
                    f'<p style="font-size:13px;font-weight:500;color:#484848;margin:0 0 4px 0;">{name}</p>'
                    f'<p style="font-size:32px;font-weight:700;color:#222222;margin:0 0 4px 0;">{ws:.1f}</p>'
                    f'<p style="font-size:13px;color:{delta_color};margin:0;">{delta}</p>',
                    variant="highlight" if is_top else "default",
                )

        # 2. Single Bar Chart
        bar_fig = create_score_bar_chart(extracted_list, weights)
        st.plotly_chart(
            bar_fig, use_container_width=True, config={"displayModeBar": False}
        )

        # 3. Deal Comparison Table
        st.markdown("##### Deal comparison")
        if findings_list and any(f.get("tco") for f in findings_list):
            table_html = _build_deal_comparison_table(
                extracted_list, findings_list, sd_lookup
            )
            st.markdown(table_html, unsafe_allow_html=True)
            st.caption(
                "Color rules: green = at or better than benchmark; "
                "yellow = within tolerance; red = outside acceptable range. "
                "Numbers are deterministic and sourced from the findings engine."
            )
        else:
            st.caption(
                "Deterministic findings unavailable for this run. "
                "Load the sample scenario to see the deal comparison table."
            )

        # 4. Risk Flags (top 5 by severity)
        st.markdown("##### Top risk flags")
        all_flags = []
        for data in extracted_list:
            supplier = data.get("supplier_name", "Unknown")
            for flag in data.get("risk_flags", []):
                all_flags.append({**flag, "supplier": supplier})

        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_flags.sort(
            key=lambda f: severity_order.get(
                str(f.get("severity", "low")).lower(), 3
            )
        )

        severity_badges = {
            "high": "badge-red",
            "medium": "badge-amber",
            "low": "badge-green",
        }

        for flag in all_flags[:5]:
            sev = str(flag.get("severity", "low")).lower()
            badge_cls = severity_badges.get(sev, "badge-green")
            desc = _esc(flag.get("description", ""))
            supplier = _esc(flag.get("supplier", ""))
            render_card(
                f'<span class="{badge_cls}">{sev.upper()}</span> &nbsp; '
                f"<strong>{supplier}</strong> &mdash; {desc}",
            )

        if not all_flags:
            st.caption("No risk flags identified.")
        elif len(all_flags) > 5:
            st.caption(
                f"Showing top 5 of {len(all_flags)} flags, sorted by severity."
            )

        # 6. Optional footer expander: per-dimension score detail
        with st.expander("View per-dimension score detail", expanded=False):
            for dim_key, dim_label in DIMENSION_LABELS.items():
                st.markdown(f"**{dim_label}**")
                cols = st.columns(len(extracted_list))

                best_score = -1.0
                best_idx = -1
                for idx, data in enumerate(extracted_list):
                    s = _get_scores_from_extracted(data)
                    if s.get(dim_key, 0) > best_score:
                        best_score = s.get(dim_key, 0)
                        best_idx = idx

                for idx, data in enumerate(extracted_list):
                    with cols[idx]:
                        s = _get_scores_from_extracted(data)
                        score_val = s.get(dim_key, 0)
                        supplier = data.get("supplier_name", f"Supplier {idx + 1}")
                        rationale = _esc(
                            _safe(data, "scores", dim_key, "rationale", default="")
                        )
                        if idx == best_idx:
                            st.markdown(
                                f"{supplier}: "
                                f'<span class="badge-coral">{score_val}/10</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(f"{supplier}: {score_val}/10")
                        st.caption(rationale)
                st.markdown("---")


# ── TAB 3: Negotiation Brief ────────────────────────────────────────────────
with tab_brief:
    if not st.session_state.get("analysis_done"):
        st.markdown(
            '<div class="placeholder-text">'
            "<p>Run an analysis to see the negotiation brief.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        comparison = st.session_state["comparison_data"]
        extracted_list = st.session_state["extracted_data"]
        findings_list = st.session_state.get("findings_per_supplier", []) or []

        # ─── Section A: Recommendation ──────────────────────────────────
        st.markdown("##### Recommendation")

        rec_supplier = comparison.get("recommended_supplier", "N/A")
        conf = str(comparison.get("confidence_level", "medium")).lower()
        conf_badges = {
            "high": "badge-green",
            "medium": "badge-amber",
            "low": "badge-red",
        }
        conf_badge = conf_badges.get(conf, "badge-amber")
        exec_summary = _esc(comparison.get("executive_summary", ""))
        exec_rationale = _esc(comparison.get("recommendation_rationale", ""))

        render_card(
            f'<p style="font-size:22px;font-weight:700;color:#222222;margin:0 0 8px 0;">'
            f'{_esc(rec_supplier)} &nbsp;'
            f'<span class="{conf_badge}">{conf.upper()} CONFIDENCE</span></p>'
            f'<p style="margin:8px 0;line-height:1.6;">{exec_summary}</p>'
            f'<p style="font-style:italic;color:#767676;font-size:13px;margin-top:12px;">'
            f"{exec_rationale}</p>",
            variant="coral",
        )

        # Grounded-in footer
        grounding_sources = comparison.get("grounding_sources", []) or []
        if grounding_sources:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown(
                '<p style="font-size:12px;color:#767676;font-weight:600;'
                'letter-spacing:0.4px;margin:0 0 6px 0;">Grounded in</p>',
                unsafe_allow_html=True,
            )
            _items_html = "".join(
                f'<li style="margin:2px 0;">'
                f"{_esc(s.get('record', ''))} &mdash; "
                f"<span style='color:#999999;'>{_esc(s.get('used_for', ''))}</span>"
                f"</li>"
                for s in grounding_sources
            )
            st.markdown(
                f'<ul style="font-size:13px;color:#767676;padding-left:18px;'
                f'margin:0 0 16px 0;list-style-type:disc;">{_items_html}</ul>',
                unsafe_allow_html=True,
            )

        # ─── Section B: What the AI Caught ──────────────────────────────
        st.markdown("##### What the AI caught")

        # Consolidate hidden risks across all suppliers
        all_hidden = []
        for fnd in findings_list:
            for r in fnd.get("hidden_risks", []) or []:
                all_hidden.append(r)

        # Severity ranking: high first, medium variants next, low last
        def _sev_rank(s):
            s = str(s).lower()
            if s == "high":
                return 0
            if s == "low":
                return 2
            return 1  # any medium-* variant

        all_hidden.sort(key=lambda r: _sev_rank(r.get("severity", "low")))

        if not all_hidden:
            st.caption(
                "No hidden findings surfaced. Run with the sample scenario "
                "to see the deterministic engine flag exit risks, compliance "
                "gaps, and pricing anomalies."
            )
        else:
            for risk in all_hidden[:5]:
                sev_raw = str(risk.get("severity", "")).lower()
                sev_label = "HIGH" if sev_raw == "high" else (
                    "LOW" if sev_raw == "low" else "MEDIUM"
                )
                badge_cls = {
                    "HIGH": "badge-red",
                    "MEDIUM": "badge-amber",
                    "LOW": "badge-green",
                }[sev_label]
                supplier = _esc(risk.get("supplier_name", ""))
                headline = _esc(risk.get("headline", ""))
                evidence = _esc(risk.get("supporting_evidence", ""))
                dollar = risk.get("dollar_impact", 0) or 0
                if dollar:
                    if abs(dollar) >= 1_000_000:
                        dollar_str = f"${dollar / 1_000_000:.2f}M"
                    elif abs(dollar) >= 1_000:
                        dollar_str = f"${dollar / 1_000:.0f}K"
                    else:
                        dollar_str = f"${dollar:,.0f}"
                    impact_html = (
                        f'<p style="margin:0 0 4px 0;color:#484848;">'
                        f"<strong>Estimated cost exposure:</strong> {dollar_str}</p>"
                    )
                else:
                    impact_html = ""

                render_card(
                    f'<p style="margin:0 0 6px 0;">'
                    f'<span class="{badge_cls}">{sev_label}</span> &nbsp; '
                    f"<strong>{supplier}</strong></p>"
                    f'<p style="margin:0 0 6px 0;font-weight:600;color:#222222;">'
                    f"{headline}</p>"
                    f"{impact_html}"
                    f'<p style="margin:0;color:#767676;font-size:13px;">{evidence}</p>',
                    variant="amber" if sev_label == "HIGH" else "default",
                )

        # ─── Section C: Negotiation Moves (recommended + top alternative) ──
        st.markdown("##### Negotiation moves")

        # Determine top alternative by weighted score (excluding recommended)
        def _ws(data):
            return compute_weighted_score(_get_scores_from_extracted(data), weights)

        scored = [
            (data.get("supplier_name", ""), _ws(data)) for data in extracted_list
        ]
        scored.sort(key=lambda t: -t[1])
        rec_name = comparison.get("recommended_supplier", "")
        alt_name = next(
            (name for name, _ in scored if name != rec_name),
            "",
        )
        targets = {n for n in [rec_name, alt_name] if n}

        strategy = comparison.get("negotiation_strategy", {}) or {}
        per_supplier = strategy.get("per_supplier", []) or []
        any_rendered = False
        for supplier_block in per_supplier:
            supplier_name = supplier_block.get("supplier_name", "")
            if supplier_name not in targets:
                continue
            any_rendered = True
            label = (
                "Recommended supplier"
                if supplier_name == rec_name
                else "Top alternative"
            )
            st.markdown(
                f'<p style="font-size:13px;color:#767676;font-weight:600;'
                f'letter-spacing:0.4px;margin:8px 0 6px 0;">'
                f"{label} &mdash; {_esc(supplier_name)}</p>",
                unsafe_allow_html=True,
            )
            for lp in supplier_block.get("leverage_points", [])[:3]:
                ask = _esc(lp.get("concrete_ask", ""))
                impact = _esc(lp.get("expected_impact", ""))
                point = _esc(lp.get("point", ""))
                render_card(
                    f'<p style="margin:0 0 4px 0;font-weight:600;color:#222222;">'
                    f"{point}</p>"
                    f'<p style="margin:0 0 4px 0;color:#484848;">'
                    f"<strong>Concrete ask:</strong> {ask}</p>"
                    f'<p style="margin:0;color:#484848;">'
                    f"<strong>Expected impact:</strong> {impact}</p>",
                )

        if not any_rendered:
            st.caption(
                "No per-supplier negotiation moves available for the "
                "recommended supplier or top alternative."
            )

        # ─── Section D: Top Risks & Mitigations (cap 3) ─────────────────
        st.markdown("##### Top risks and mitigations")
        for idx, risk in enumerate(comparison.get("top_risks", [])[:3], 1):
            affected = ", ".join(_esc(s) for s in risk.get("affected_suppliers", []))
            risk_desc = _esc(risk.get("risk", ""))
            mitigation = _esc(risk.get("mitigation", ""))
            render_card(
                f'<p style="margin:0 0 6px 0;"><strong>{idx}. {risk_desc}</strong></p>'
                f'<p style="margin:0 0 6px 0;"><strong>Mitigation:</strong> {mitigation}</p>'
                f'<p style="margin:0;"><em>Affects:</em> '
                f'<span class="badge-amber">{affected}</span></p>',
            )

        # ─── Section E: Clarification Questions (cap 5) ─────────────────
        st.markdown("##### Clarification questions")
        cq = comparison.get("clarification_questions", [])[:5]
        if cq:
            df = pd.DataFrame(
                [
                    {
                        "Question": _esc(q.get("question", "")),
                        "Directed To": _esc(q.get("directed_to", "")),
                        "Why It Matters": _esc(q.get("why_it_matters", "")),
                    }
                    for q in cq
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("No clarification questions generated.")

        # ─── Section F: Stress Test (what could go wrong cap 3) ─────────
        st.markdown("##### Stress test")
        stress = comparison.get("stress_test", {}) or {}
        wrong_items = (stress.get("what_could_go_wrong", []) or [])[:3]
        wrong_html = "".join(f"<li>{_esc(item)}</li>" for item in wrong_items)
        cont = _esc(stress.get("contingency_recommendation", ""))
        cont_html = (
            f'<p style="margin:12px 0 0 0;"><strong>Contingency:</strong> {cont}</p>'
            if cont
            else ""
        )
        render_card(
            f'<p style="margin:0 0 8px 0;"><strong>What could go wrong</strong></p>'
            f'<ul style="margin:0;padding-left:20px;">{wrong_html}</ul>'
            f"{cont_html}",
            variant="amber",
        )

        # ─── Section G: Export ──────────────────────────────────────────
        st.markdown("##### Export")
        pdf_bytes = st.session_state.get("pdf_report")
        if pdf_bytes:
            today = datetime.date.today().strftime("%Y-%m-%d")
            st.download_button(
                label="Download Full Report (PDF)",
                data=pdf_bytes,
                file_name=f"proposal_analysis_{today}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ── Analysis pipeline (triggered by sidebar button) ────────────────────────
if inline_analyze:
    import anthropic

    # Build a lookup of structured_data from the loaded sample (if any).
    # Custom (paste/upload) proposals won't have structured_data and will
    # therefore skip the deterministic findings step.
    structured_lookup = {
        p["supplier_name"]: p.get("structured_data")
        for p in SAMPLE_PROPOSALS.get("proposals", [])
    }

    proposals = []
    for i in range(st.session_state["num_suppliers"]):
        name = st.session_state.get(f"supplier_{i}_name", "").strip()
        text = st.session_state.get(f"supplier_{i}_text", "").strip()
        if name and text:
            proposals.append({
                "supplier_name": name,
                "proposal_text": text,
                "structured_data": structured_lookup.get(name),
            })

    if len(proposals) < 2:
        st.error("Please provide at least 2 proposals with names and text.")
        st.stop()

    if total_weight != 100:
        st.error(f"Weights must sum to 100%. Currently: {total_weight}%")
        st.stop()

    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    # Build the sourcing-context block once. All extract + compare prompts use it.
    context_block = build_context_block(AIRBNB_CONTEXT)

    extracted_results = []
    findings_per_supplier: list[dict] = []

    with st.status("Analyzing proposals...", expanded=True) as status:
        # Extract each proposal -- with deterministic findings if available
        for idx, prop in enumerate(proposals):
            sd = prop.get("structured_data")
            if sd:
                st.write(f"Computing deterministic findings for **{prop['supplier_name']}**...")
                engine_input = adapt_structured_for_engine(prop["supplier_name"], sd)
                findings = run_all_findings(engine_input, AIRBNB_CONTEXT)
                findings_summary = json.dumps(findings, indent=2, default=str)
            else:
                findings = {
                    "supplier_name": prop["supplier_name"],
                    "note": "No structured_data available; deterministic findings skipped.",
                }
                findings_summary = json.dumps(findings, indent=2)
            findings_per_supplier.append(findings)

            st.write(f"Extracting terms from **{prop['supplier_name']}**...")
            prompts = get_extract_prompt(
                prop["supplier_name"],
                prop["proposal_text"],
                context_block=context_block,
                findings_summary=findings_summary,
            )
            result = call_claude(client, prompts["system"], prompts["user"])
            if result is None:
                status.update(label="Analysis failed", state="error")
                st.stop()
            extracted_results.append(result)
            st.write(f"Extracted **{prop['supplier_name']}** successfully.")

        # Comparative analysis
        st.write("Generating comparative analysis...")
        scenario = (
            SAMPLE_PROPOSALS["scenario_name"]
            if use_sample
            else "Custom Proposal Comparison"
        )
        compare_prompts = get_compare_prompt(
            extracted_results,
            weights,
            scenario,
            context_block=context_block,
            all_findings=findings_per_supplier,
        )
        comparison_result = call_claude(
            client, compare_prompts["system"], compare_prompts["user"]
        )
        if comparison_result is None:
            status.update(label="Comparison failed", state="error")
            st.stop()

        st.write("Generating PDF report...")
        pdf_bytes = generate_pdf_report(
            comparison_result, extracted_results, weights, scenario
        )

        status.update(label="Analysis complete!", state="complete")

    # Store results
    st.session_state["extracted_data"] = extracted_results
    st.session_state["comparison_data"] = comparison_result
    st.session_state["pdf_report"] = pdf_bytes
    st.session_state["findings_per_supplier"] = findings_per_supplier
    st.session_state["analysis_done"] = True
    st.session_state["just_analyzed"] = True
    st.rerun()
