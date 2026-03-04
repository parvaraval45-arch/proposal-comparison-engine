"""Proposal Comparison Engine -- Main Streamlit application."""

from __future__ import annotations

import datetime
import json
import pathlib
import re

import streamlit as st

from prompts import (
    COMPARE_SCHEMA,
    EXTRACT_SCHEMA,
    get_compare_prompt,
    get_extract_prompt,
)
from sample_data import SAMPLE_PROPOSALS
from utils import (
    DIMENSION_LABELS,
    _get_scores_from_extracted,
    compute_weighted_score,
    create_radar_chart,
    create_score_bar_chart,
    generate_pdf_report,
    parse_pdf,
)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Proposal Comparison Engine",
    page_icon="\U0001f4ca",
    layout="wide",
)

# ── Airbnb Custom CSS ───────────────────────────────────────────────────────
AIRBNB_CSS = """
<style>
/* ── Global ────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: -apple-system, "Cereal", "Helvetica Neue", Helvetica, Arial, sans-serif;
    color: #484848;
}

/* Remove Streamlit top padding */
.block-container { padding-top: 2rem !important; max-width: 1200px; }

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
    padding: 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
.airbnb-card-coral {
    background: #FFFFFF;
    border: 1px solid #EBEBEB;
    border-left: 3px solid #FF5A5F;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
.airbnb-card-amber {
    background: #FFFFFF;
    border: 1px solid #EBEBEB;
    border-left: 3px solid #FFB400;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
.airbnb-card-highlight {
    background: #FFFFFF;
    border: 2px solid #FF5A5F;
    border-radius: 12px;
    padding: 24px;
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
.divider { border: none; border-top: 1px solid #EBEBEB; margin: 16px 0; }

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
st.session_state.setdefault("w_cost", 25)
st.session_state.setdefault("w_scope", 20)
st.session_state.setdefault("w_reliability", 20)
st.session_state.setdefault("w_risk", 15)
st.session_state.setdefault("w_flexibility", 10)
st.session_state.setdefault("w_esg", 10)

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
    f'<p class="app-header-title">Supplier Proposal Comparison Engine</p>'
    f'<p class="app-header-sub">AI&#8209;augmented sourcing intelligence</p>'
    f'</div></div>'
    f'<hr class="divider">',
    unsafe_allow_html=True,
)

# Success banner after analysis
if st.session_state.get("just_analyzed"):
    st.markdown(
        '<div class="success-banner">'
        "Analysis complete! Switch to the <strong>Comparison Matrix</strong> or "
        "<strong>Negotiation Brief</strong> tabs to see results."
        "</div>",
        unsafe_allow_html=True,
    )
    st.session_state["just_analyzed"] = False

# Context banner (collapsible)
with st.expander("Where This Fits in the Sourcing Operating Model", expanded=False):
    st.markdown(
        """
- **Stage**: Post-RFP proposal evaluation — after suppliers have submitted and before shortlist decisions
- **Users**: Sourcing analysts and category managers preparing evaluation summaries for leadership
- **Decisions informed**: Supplier shortlisting, negotiation strategy, and clarification round planning — not final contract sign-off
- **Human validation required**: All AI-generated scores and recommendations must be reviewed by a sourcing professional before action
""",
    )


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

    w_cost = st.slider("Cost Competitiveness", 0, 50, step=5, key="w_cost")
    w_scope = st.slider("Scope & Quality", 0, 50, step=5, key="w_scope")
    w_reliability = st.slider("Service Reliability", 0, 50, step=5, key="w_reliability")
    w_risk = st.slider("Risk Profile", 0, 50, step=5, key="w_risk")
    w_flexibility = st.slider("Flexibility", 0, 50, step=5, key="w_flexibility")
    w_esg = st.slider("ESG Alignment", 0, 50, step=5, key="w_esg")

    total_weight = w_cost + w_scope + w_reliability + w_risk + w_flexibility + w_esg
    if total_weight != 100:
        st.warning(f"Weights must sum to 100%. Currently: {total_weight}%")
    else:
        st.success("Weights sum to 100%")

    weights = {
        "cost_competitiveness": w_cost,
        "scope_quality": w_scope,
        "service_reliability": w_reliability,
        "risk_profile": w_risk,
        "flexibility": w_flexibility,
        "esg_alignment": w_esg,
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


# ── Main content — 3 Tabs ──────────────────────────────────────────────────
tab_input, tab_compare, tab_brief = st.tabs(
    ["\U0001f4c4 Input Proposals", "\U0001f4ca Comparison Matrix", "\U0001f4cb Negotiation Brief"]
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
        "Run Comparison & Generate Negotiation Brief  \u2192",
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
with tab_compare:
    if not st.session_state.get("analysis_done"):
        st.markdown(
            '<div class="placeholder-text">'
            '<p style="font-size:40px;margin-bottom:8px;">\U0001f4ca</p>'
            "<p>Run an analysis to see the comparison matrix</p></div>",
            unsafe_allow_html=True,
        )
    else:
        extracted_list = st.session_state["extracted_data"]
        comparison = st.session_state["comparison_data"]

        # Section A: Overall Scores
        st.markdown("##### Overall Weighted Scores")
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

        # Bar chart
        bar_fig = create_score_bar_chart(extracted_list, weights)
        st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": False})

        # Section B: Radar Chart
        st.markdown("##### Dimension Scores")
        radar_fig = create_radar_chart(extracted_list, weights)
        st.plotly_chart(radar_fig, use_container_width=True, config={"displayModeBar": False})

        # Section C: Extracted Terms Comparison
        st.markdown("##### Extracted Terms Comparison")

        term_categories = {
            "Pricing": "pricing",
            "Scope & Deliverables": "scope_and_deliverables",
            "Service Levels": "service_levels",
            "Risk Factors": "risk_factors",
            "Flexibility": "flexibility",
            "ESG & Diversity": "esg_and_diversity",
        }

        for cat_label, cat_key in term_categories.items():
            with st.expander(cat_label, expanded=False):
                cols = st.columns(len(extracted_list))
                for idx, data in enumerate(extracted_list):
                    with cols[idx]:
                        supplier = data.get("supplier_name", f"Supplier {idx + 1}")
                        st.markdown(f"**{supplier}**")
                        terms = _safe(data, "extracted_terms", cat_key, default={})
                        if isinstance(terms, dict):
                            for field, value in terms.items():
                                label = field.replace("_", " ").title()
                                if isinstance(value, list):
                                    items = (
                                        ", ".join(_esc(v) for v in value)
                                        if value
                                        else "None listed"
                                    )
                                    st.markdown(f"**{label}**: {items}")
                                elif value is None:
                                    st.markdown(f"**{label}**: *Not specified*")
                                else:
                                    st.markdown(f"**{label}**: {_esc(value)}")
                        st.markdown("---")

        # Section D: Risk Flags
        st.markdown("##### Risk Flags")

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

        severity_icons = {
            "high": "\U0001f534",
            "medium": "\U0001f7e1",
            "low": "\U0001f7e2",
        }
        severity_badges = {
            "high": "badge-red",
            "medium": "badge-amber",
            "low": "badge-green",
        }

        for flag in all_flags:
            sev = str(flag.get("severity", "low")).lower()
            icon = severity_icons.get(sev, "\u26aa")
            badge_cls = severity_badges.get(sev, "badge-green")
            desc = _esc(flag.get("description", ""))
            supplier = _esc(flag.get("supplier", ""))
            render_card(
                f'{icon} <span class="{badge_cls}">{sev.upper()}</span> &nbsp; '
                f"<strong>{supplier}</strong> &mdash; {desc}",
            )

        if not all_flags:
            st.caption("No risk flags identified.")

        # Section E: Score Breakdown
        st.markdown("##### Score Breakdown by Dimension")
        for dim_key, dim_label in DIMENSION_LABELS.items():
            with st.expander(dim_label, expanded=False):
                cols = st.columns(len(extracted_list))

                # Find best score for this dimension
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
                        rationale = _esc(_safe(
                            data, "scores", dim_key, "rationale", default=""
                        ))

                        if idx == best_idx:
                            st.markdown(
                                f"**{supplier}**: "
                                f'<span class="badge-coral">{score_val}/10</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(f"**{supplier}**: {score_val}/10")

                        st.caption(rationale)


# ── TAB 3: Negotiation Brief ────────────────────────────────────────────────
with tab_brief:
    if not st.session_state.get("analysis_done"):
        st.markdown(
            '<div class="placeholder-text">'
            '<p style="font-size:40px;margin-bottom:8px;">\U0001f4cb</p>'
            "<p>Run an analysis to see the negotiation brief</p></div>",
            unsafe_allow_html=True,
        )
    else:
        comparison = st.session_state["comparison_data"]
        extracted_list = st.session_state["extracted_data"]

        # Section A: Executive Recommendation
        st.markdown("##### Executive Recommendation")

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
            f'{rec_supplier} &nbsp;'
            f'<span class="{conf_badge}">{conf.upper()} CONFIDENCE</span></p>'
            f'<p style="margin:8px 0;line-height:1.6;">{exec_summary}</p>'
            f'<p style="font-style:italic;color:#767676;font-size:13px;margin-top:12px;">'
            f"{exec_rationale}</p>"
            f'<p style="font-style:italic;color:#767676;font-size:12px;margin-top:8px;">'
            f"Recommendation based on weighted criteria analysis. Final decision "
            f"should consider strategic context, relationship history, and factors "
            f"beyond this quantitative assessment.</p>",
            variant="coral",
        )

        # Section B: Comparative Highlights
        st.markdown("##### Comparative Highlights")
        highlights = comparison.get("comparative_highlights", [])
        for h in highlights:
            leader = _esc(h.get("leader", ""))
            dimension = _esc(h.get("dimension", ""))
            insight = _esc(h.get("insight", ""))
            render_card(
                f'<p style="margin:0 0 6px 0;"><strong>{dimension}</strong> &nbsp; '
                f'<span class="badge-teal">{leader}</span></p>'
                f'<p style="margin:0;color:#484848;">{insight}</p>',
            )

        # Section C: Top Risks
        st.markdown("##### Top Risks")
        for idx, risk in enumerate(comparison.get("top_risks", []), 1):
            affected = ", ".join(_esc(s) for s in risk.get("affected_suppliers", []))
            risk_desc = _esc(risk.get("risk", ""))
            mitigation = _esc(risk.get("mitigation", ""))
            render_card(
                f'<p style="margin:0 0 6px 0;"><strong>{idx}. {risk_desc}</strong></p>'
                f'<p style="margin:0 0 6px 0;"><strong>Mitigation</strong>: {mitigation}</p>'
                f'<p style="margin:0;"><em>Affects</em>: <span class="badge-amber">{affected}</span></p>',
            )

        # Section D: Negotiation Strategy
        st.markdown("##### Negotiation Strategy")
        strategy = comparison.get("negotiation_strategy", {})
        for supplier_block in strategy.get("per_supplier", []):
            supplier_name = supplier_block.get("supplier_name", "Unknown")
            with st.expander(
                f"Leverage Points: {supplier_name}", expanded=False
            ):
                for lp in supplier_block.get("leverage_points", []):
                    point = _esc(lp.get("point", ""))
                    ask = _esc(lp.get("concrete_ask", ""))
                    impact = _esc(lp.get("expected_impact", ""))
                    render_card(
                        f'<p style="margin:0 0 4px 0;"><strong>{point}</strong></p>'
                        f'<p style="margin:0 0 4px 0;"><strong>Concrete ask</strong>: {ask}</p>'
                        f'<p style="margin:0;"><strong>Expected impact</strong>: {impact}</p>',
                    )

        tactics = strategy.get("general_tactics", [])
        if tactics:
            tactics_html = "".join(f"<li>{_esc(t)}</li>" for t in tactics)
            render_card(
                f'<p style="margin:0 0 8px 0;"><strong>General Negotiation Tactics</strong></p>'
                f'<ul style="margin:0;padding-left:20px;">{tactics_html}</ul>',
            )

        # Section E: Clarification Questions
        st.markdown("##### Clarification Questions")
        cq = comparison.get("clarification_questions", [])
        if cq:
            import pandas as pd

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

        # Section F: Stress Test
        st.markdown("##### Stress Test")
        stress = comparison.get("stress_test", {})
        wrong_items = stress.get("what_could_go_wrong", [])
        wrong_html = "".join(f"<li>{_esc(item)}</li>" for item in wrong_items)
        cont = _esc(stress.get("contingency_recommendation", ""))
        cont_html = (
            f'<p style="margin:12px 0 0 0;"><strong>Contingency Recommendation</strong>: {cont}</p>'
            if cont else ""
        )
        render_card(
            f'<p style="margin:0 0 8px 0;"><strong>What Could Go Wrong</strong></p>'
            f'<ul style="margin:0;padding-left:20px;">{wrong_html}</ul>'
            f'{cont_html}',
            variant="amber",
        )

        # Section G: Download Report
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

    proposals = []
    for i in range(st.session_state["num_suppliers"]):
        name = st.session_state.get(f"supplier_{i}_name", "").strip()
        text = st.session_state.get(f"supplier_{i}_text", "").strip()
        if name and text:
            proposals.append({"supplier_name": name, "proposal_text": text})

    if len(proposals) < 2:
        st.error("Please provide at least 2 proposals with names and text.")
        st.stop()

    if total_weight != 100:
        st.error(f"Weights must sum to 100%. Currently: {total_weight}%")
        st.stop()

    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    extracted_results = []

    with st.status("Analyzing proposals...", expanded=True) as status:
        # Extract each proposal
        for idx, prop in enumerate(proposals):
            st.write(f"Extracting terms from **{prop['supplier_name']}**...")
            prompts = get_extract_prompt(
                prop["supplier_name"], prop["proposal_text"]
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
            extracted_results, weights, scenario
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
    st.session_state["analysis_done"] = True
    st.session_state["just_analyzed"] = True
    st.rerun()
