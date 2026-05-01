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
        "contract_flexibility": {
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
        "tco_budget_fit": {"score": "0-10", "rationale": "string"},
        "pricing_vs_benchmark": {"score": "0-10", "rationale": "string"},
        "risk_profile": {"score": "0-10", "rationale": "string"},
        "integration_readiness": {"score": "0-10", "rationale": "string"},
        "operational_reliability": {"score": "0-10", "rationale": "string"},
        "strategic_optionality": {"score": "0-10", "rationale": "string"},
        "esg_diversity": {"score": "0-10", "rationale": "string"},
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
    "You are a Senior Strategic Sourcing Analyst specializing in software "
    "renewals for the Data & Analytics category at a major technology company, "
    "with 15+ years of experience evaluating multi-year SaaS agreements.\n\n"
    "Your task is to analyze a single supplier proposal and extract structured "
    "commercial terms, score the proposal against the 7 evaluation dimensions "
    "below, identify risks, and surface negotiation leverage points.\n\n"
    "THE SEVEN EVALUATION DIMENSIONS (calibrated for software renewal):\n"
    "1. tco_budget_fit -- TCO & Budget Fit. Evaluates 3-year cost envelope "
    "alignment with FP&A budget. Considers tiered net pricing across the seat "
    "forecast, support uplift, implementation fee, and any hidden cost flags. "
    "A vendor is rewarded for landing under or near budget across all 3 years.\n"
    "2. pricing_vs_benchmark -- Pricing vs Benchmark. Scores against market "
    "P10 / Median / P90 for $/user/year, implementation fee as % of TCV, "
    "annual support %, uptime SLA, SLA credit %, and termination notice days. "
    "Reward proposals at or below median on cost-side metrics and at or above "
    "median on value-side metrics.\n"
    "3. risk_profile -- Risk Profile. Combines compliance certifications "
    "(SOC 2 Type II, ISO 27001, GDPR Article 28), data residency coverage, "
    "and exit terms (penalty formula severity, notice period). Penalize "
    "single-region residency, missing Type II, and punitive exit penalties.\n"
    "4. integration_readiness -- Integration Readiness. Evaluates fit against "
    "named engineering dependencies: SSO with SCIM, Lakehouse / Snowflake "
    "connector, Role-Based Access Controls, and streaming API. Reward proven "
    "capability with documented, supported integrations; penalize roadmap "
    "promises and missing capabilities.\n"
    "5. operational_reliability -- Operational Reliability. Uptime SLA, SLA "
    "credit %, support coverage hours (24x5 vs 24x7), severity-1 response "
    "commitments, named TAM availability. Vague best-effort commitments "
    "score lower than measurable guarantees with automatic credits.\n"
    "6. strategic_optionality -- Strategic Optionality. Termination flexibility, "
    "tier banding fairness as the seat forecast crosses breakpoints, list-price "
    "lock vs CPI escalation, data portability, and renewal terms. Reward "
    "vendors who minimize lock-in.\n"
    "7. esg_diversity -- ESG & Diversity. Supplier diversity certifications "
    "(MBE, WBE, LGBTBE, SDVOSB), sustainability commitments (B Corp, carbon "
    "neutrality), and DEI posture. Tiebreaker dimension, lower default weight.\n\n"
    "EVALUATION PRINCIPLES:\n"
    "- Apply Total Cost of Ownership (TCO) thinking, not just sticker price. "
    "Flag hidden costs: T&M markups, change order rates, price escalation "
    "clauses, and ambiguous add-ons.\n"
    "- Evaluate SLAs for specificity and enforceability. Vague commitments "
    '("best effort," "typically") score lower than measurable guarantees '
    '("99.95% with 20% MRR credit per incident").\n'
    "- Score each dimension 0-10 with clear rationale. Be rigorous: most "
    "proposals score 4-8. Reserve 9-10 for genuinely exceptional terms. "
    "Reserve 0-3 for clearly deficient areas.\n"
    "- When information is missing or ambiguous, note it explicitly as a gap. "
    "Missing information should negatively impact the relevant score.\n\n"
    "OUTPUT: Return ONLY valid JSON matching the schema below. No markdown, "
    "no preamble, no explanation outside JSON."
)

SYSTEM_PROMPT_COMPARE = (
    "You are a Senior Strategic Sourcing Analyst specializing in software "
    "renewals for the Data & Analytics category, preparing a decision brief "
    "for sourcing leadership. You have analyzed individual proposals against "
    "the 7-dimension scoring model (tco_budget_fit, pricing_vs_benchmark, "
    "risk_profile, integration_readiness, operational_reliability, "
    "strategic_optionality, esg_diversity) and now need to synthesize them "
    "into a comparative recommendation.\n\n"
    "Your audience is a VP of Procurement who cares about:\n"
    "1. Clear recommendation with confidence level (high/medium/low)\n"
    "2. Key differentiators across the 7 evaluation dimensions -- not just "
    "scores but WHY one supplier is better in each dimension\n"
    "3. Top 3 risks regardless of supplier chosen, with emphasis on TCO "
    "drift, exit penalty exposure, integration gaps, and compliance "
    "posture\n"
    "4. Specific, actionable negotiation leverage points per supplier\n"
    "5. What to demand in clarification rounds before final decision\n\n"
    "ANALYSIS PRINCIPLES:\n"
    "- The best supplier is NOT always the cheapest. Weigh total value: "
    "TCO and budget fit, pricing vs benchmark, risk profile, integration "
    "readiness, operational reliability, strategic optionality, and ESG & "
    "diversity all matter.\n"
    "- Identify where suppliers are similar (commodity terms) vs. where they "
    "differentiate (strategic terms). Focus negotiation on differentiation "
    "gaps.\n"
    "- For each leverage point, specify the CONCRETE ask (e.g., 'Push net "
    "price from $247 to $230 in Tier 2' not 'negotiate better pricing').\n"
    "- Flag areas where ALL proposals are weak -- this signals a requirement "
    "gap in the RFP or a category-wide market limitation.\n"
    "- Include a 'stress test' section: what could go wrong with the "
    "recommended supplier? Leadership respects analysts who challenge their "
    "own recommendations.\n"
    "- Recommendation is based on weighted criteria scoring across the 7 "
    "dimensions. Always note: 'Final decision should consider strategic "
    "context, relationship history, and factors beyond this analysis.'\n\n"
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
        ``{"tco_budget_fit": 25, "pricing_vs_benchmark": 15, ...}``.
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
