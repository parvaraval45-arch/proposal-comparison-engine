"""Claude API prompt templates and JSON schemas for proposal analysis."""

import json


# ---------------------------------------------------------------------------
# JSON Schemas
# ---------------------------------------------------------------------------

EXTRACT_SCHEMA = {
    "supplier_name": "string",
    "extracted_terms": {
        "pricing": {
            "total_contract_value": "string",
            "pricing_model": "string (Fixed fee / T&M / Per-unit / Subscription / Hybrid)",
            "payment_terms": "string",
            "price_escalation_clause": "string or null",
            "discount_or_incentives": "string or null",
            "hidden_cost_flags": ["string"],
        },
        "scope_and_deliverables": {
            "summary": "string (2-3 sentences)",
            "key_deliverables": ["string"],
            "out_of_scope_items": ["string"],
            "timeline": "string",
        },
        "service_levels": {
            "sla_commitments": ["string"],
            "escalation_process": "string or null",
            "performance_penalties": "string or null",
            "reporting_cadence": "string or null",
        },
        "risk_factors": {
            "financial_stability_signals": "string",
            "geographic_concentration": "string or null",
            "key_person_dependency": "string or null",
            "data_privacy_provisions": "string or null",
            "insurance_coverage": "string or null",
            "identified_risks": ["string"],
        },
        "flexibility": {
            "termination_clause": "string",
            "change_order_process": "string or null",
            "scaling_provisions": "string or null",
            "renewal_terms": "string or null",
        },
        "esg_and_diversity": {
            "diversity_certifications": ["string"],
            "sustainability_commitments": "string or null",
            "esg_reporting": "string or null",
        },
    },
    "scores": {
        "cost_competitiveness": {"score": "0-10", "rationale": "string"},
        "scope_quality": {"score": "0-10", "rationale": "string"},
        "service_reliability": {"score": "0-10", "rationale": "string"},
        "risk_profile": {"score": "0-10", "rationale": "string"},
        "flexibility": {"score": "0-10", "rationale": "string"},
        "esg_alignment": {"score": "0-10", "rationale": "string"},
    },
    "risk_flags": [
        {"severity": "high|medium|low", "description": "string"},
    ],
    "negotiation_leverage": [
        {"point": "string", "rationale": "string", "suggested_ask": "string"},
    ],
}

COMPARE_SCHEMA = {
    "executive_summary": "string (3-4 sentences)",
    "recommended_supplier": "string",
    "confidence_level": "high|medium|low",
    "recommendation_rationale": "string (2-3 sentences)",
    "comparative_highlights": [
        {
            "dimension": "string",
            "insight": "string",
            "leader": "string (supplier name)",
        },
    ],
    "top_risks": [
        {
            "risk": "string",
            "mitigation": "string",
            "affected_suppliers": ["string"],
        },
    ],
    "negotiation_strategy": {
        "per_supplier": [
            {
                "supplier_name": "string",
                "leverage_points": [
                    {
                        "point": "string",
                        "concrete_ask": "string",
                        "expected_impact": "string",
                    },
                ],
            },
        ],
        "general_tactics": ["string"],
    },
    "clarification_questions": [
        {
            "question": "string",
            "directed_to": "string (supplier name or 'All')",
            "why_it_matters": "string",
        },
    ],
    "stress_test": {
        "what_could_go_wrong": ["string"],
        "contingency_recommendation": "string",
    },
}


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_EXTRACT = (
    "You are a Senior Strategic Sourcing Analyst at a major technology company "
    "with 15+ years of experience evaluating supplier proposals across enterprise "
    "technology, professional services, marketing, and operations categories.\n\n"
    "Your task is to analyze a single supplier proposal and extract structured "
    "commercial terms, score the proposal against evaluation criteria, identify "
    "risks, and surface negotiation leverage points.\n\n"
    "EVALUATION PRINCIPLES:\n"
    "- Apply Total Cost of Ownership (TCO) thinking, not just sticker price. "
    "Flag hidden costs: integration fees, travel expenses, change order markups, "
    "price escalation clauses, and ambiguous add-ons.\n"
    "- Evaluate SLAs for specificity and enforceability. Vague commitments "
    '("best effort," "typically") score lower than measurable guarantees '
    '("99% on-time with 5% credit per incident").\n'
    "- Assess risk through a procurement lens: supplier financial stability, "
    "key-person dependency, geographic concentration, data handling, insurance "
    "adequacy, and business continuity.\n"
    "- Value flexibility and optionality: favorable termination clauses, scaling "
    "provisions, and change order processes reduce lock-in risk.\n"
    "- ESG alignment includes supplier diversity certifications (MBE, WBE, "
    "LGBTBE, SDVOSB, HUBZone), sustainability commitments (B Corp, carbon "
    "neutrality), and alignment with belonging-centered values.\n"
    "- Score each dimension 0\u201310 with clear rationale. Be rigorous: most "
    "proposals score 4\u20138. Reserve 9\u201310 for genuinely exceptional terms. "
    "Reserve 0\u20133 for clearly deficient areas.\n"
    "- When information is missing or ambiguous, note it explicitly as a gap. "
    "Missing information should negatively impact the relevant score.\n\n"
    "OUTPUT: Return ONLY valid JSON matching the schema below. No markdown, "
    "no preamble, no explanation outside JSON."
)

SYSTEM_PROMPT_COMPARE = (
    "You are a Senior Strategic Sourcing Analyst preparing a decision brief "
    "for sourcing leadership. You have analyzed individual proposals and now "
    "need to synthesize them into a comparative recommendation.\n\n"
    "Your audience is a VP of Procurement who cares about:\n"
    "1. Clear recommendation with confidence level (high/medium/low)\n"
    "2. Key differentiators between suppliers \u2014 not just scores but WHY one "
    "is better\n"
    "3. Top 3 risks regardless of supplier chosen\n"
    "4. Specific, actionable negotiation leverage points per supplier\n"
    "5. What to demand in clarification rounds before final decision\n\n"
    "ANALYSIS PRINCIPLES:\n"
    "- The best supplier is NOT always the cheapest. Weigh total value: scope "
    "quality, risk reduction, strategic alignment, and flexibility all matter.\n"
    "- Identify where suppliers are similar (commodity terms) vs. where they "
    "differentiate (strategic terms). Focus negotiation on differentiation gaps.\n"
    "- For each leverage point, specify the CONCRETE ask (e.g., \u201cPush for "
    "Net 60 instead of Net 30\u201d not \u201cnegotiate better payment terms\u201d).\n"
    "- Flag areas where ALL proposals are weak \u2014 this signals a requirement "
    "gap in the RFP or category-wide market limitation.\n"
    "- Include a \u201cstress test\u201d section: what could go wrong with the "
    "recommended supplier? Leadership respects analysts who challenge their "
    "own recommendations.\n"
    "- Recommendation is based on weighted criteria scoring. Always note: "
    "\u201cFinal decision should consider strategic context, relationship history, "
    "and factors beyond this analysis.\u201d\n\n"
    "Use the following evaluation weights: {weights_json}\n\n"
    "OUTPUT: Return ONLY valid JSON matching the schema below. No markdown, "
    "no preamble."
)


# ---------------------------------------------------------------------------
# User Prompts
# ---------------------------------------------------------------------------

USER_PROMPT_EXTRACT = (
    "Analyze the following supplier proposal. Extract all commercial terms, "
    "score against the 6 evaluation dimensions, identify risk flags, and "
    "surface negotiation leverage points.\n\n"
    "Supplier Name: {supplier_name}\n\n"
    "Proposal Text:\n"
    "---\n"
    "{proposal_text}\n"
    "---\n\n"
    "Return your analysis as JSON matching this exact schema:\n"
    "{json_schema}"
)

USER_PROMPT_COMPARE = (
    "Here are the individual analyses of {num_suppliers} supplier proposals "
    "for: {scenario_name}\n\n"
    "{all_extracted_data_json}\n\n"
    "Return your comparative analysis as JSON matching this exact schema:\n"
    "{comparison_schema}"
)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_extract_prompt(supplier_name: str, proposal_text: str) -> dict:
    """Build the system + user messages for single-proposal extraction.

    Returns a dict with ``system`` and ``user`` keys containing the
    formatted prompt strings ready for the Claude API.
    """
    formatted_user = USER_PROMPT_EXTRACT.format(
        supplier_name=supplier_name,
        proposal_text=proposal_text,
        json_schema=json.dumps(EXTRACT_SCHEMA, indent=2),
    )
    return {
        "system": SYSTEM_PROMPT_EXTRACT,
        "user": formatted_user,
    }


def get_compare_prompt(
    extracted_data_list: list[dict],
    weights: dict,
    scenario_name: str,
) -> dict:
    """Build the system + user messages for comparative analysis.

    Parameters
    ----------
    extracted_data_list:
        List of per-supplier extraction results (dicts).
    weights:
        Evaluation dimension weights, e.g.
        ``{"cost_competitiveness": 25, "scope_quality": 20, ...}``.
    scenario_name:
        Human-readable name of the sourcing scenario.

    Returns a dict with ``system`` and ``user`` keys.
    """
    formatted_system = SYSTEM_PROMPT_COMPARE.format(
        weights_json=json.dumps(weights, indent=2),
    )
    formatted_user = USER_PROMPT_COMPARE.format(
        num_suppliers=len(extracted_data_list),
        scenario_name=scenario_name,
        all_extracted_data_json=json.dumps(extracted_data_list, indent=2),
        comparison_schema=json.dumps(COMPARE_SCHEMA, indent=2),
    )
    return {
        "system": formatted_system,
        "user": formatted_user,
    }
