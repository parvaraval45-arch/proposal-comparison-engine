"""Pure-Python findings engine for supplier proposals.

The LLM never does math; it only narrates. Every numerical finding —
TCO, benchmark deltas, budget alignment, integration coverage, exit
costs, hidden risks — is computed deterministically here.

All public functions are pure: identical inputs yield identical outputs,
no side effects, no mutation of arguments.

Supplier dict schema
--------------------
::

    supplier = {
        "supplier_name": str,

        # Pricing / TCO inputs (raw)
        "net_price": float,                       # $ per user per year
        "support_pct": float,                     # percent of license, e.g. 12.0
        "implementation_fee": float,              # flat $ paid in year 1

        # Benchmark inputs (in benchmark units)
        "uptime_sla_pct": float,                  # e.g. 99.95
        "sla_credit_pct": float,                  # e.g. 10.0  ( % of MRR )
        "termination_notice_days": int,           # e.g. 60

        # Exit / termination
        "termination_penalty": {
            "type": "none" | "fixed" | "pct_of_remaining_tcv",
            "value": float,                       # $ for fixed, percent for pct_of_remaining_tcv
        },

        # Compliance / data
        "certs": list[str],                       # e.g. ["SOC 2 Type II", "ISO 27001"]
        "data_residency": str,                    # e.g. "single-region (us-east-1)" or "multi-region"
    }

Sample fixtures for AlphaBI, BeaconIQ, and DataNova are at the bottom
of this file under ``SAMPLE_SUPPLIERS``.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from airbnb_context import (
    AIRBNB_CONTEXT,
    IndustryBenchmark,
    SourcingContext,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTRACT_FISCAL_YEARS = ("FY-2025", "FY-2026", "FY-2027")

TIER_BREAKPOINTS = (1000, 5000)  # ≤1000 = tier 1, 1001–5000 = tier 2, >5000 = tier 3


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TCOResult:
    year_breakdown: List[Dict[str, Any]]
    total_3yr_tco: float
    license_total: float
    support_total: float
    implementation: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seats_for_fy(context: SourcingContext, fy: str) -> int:
    """Return forecasted seat count for a fiscal year, or 0 if missing."""
    for u in context.usage:
        if u.fiscal_year == fy:
            return u.expected_seats
    return 0


def _tier_for_seats(seats: int) -> int:
    """Return tier band for a seat count.

    ≤1000 → tier 1, 1001–4999 → tier 2, ≥5000 → tier 3.
    (Spec: 'exactly 5000 = tier 3'.)
    """
    if seats <= TIER_BREAKPOINTS[0]:
        return 1
    if seats < TIER_BREAKPOINTS[1]:
        return 2
    return 3


def _benchmark_by_metric(context: SourcingContext, metric: str) -> IndustryBenchmark:
    for b in context.benchmarks:
        if b.metric == metric:
            return b
    raise KeyError(f"Benchmark metric not found: {metric}")


def _budget_for_fy(context: SourcingContext, fy: str):
    for envelope in context.budget:
        if envelope.fiscal_year == fy:
            return envelope
    return None


def _classify_position(value: float, p10: float, median: float, p90: float) -> str:
    """Return one of: below_p10, p10_to_median, at_median, median_to_p90, above_p90."""
    if value < p10:
        return "below_p10"
    if value == median:
        return "at_median"
    if value <= median:
        return "p10_to_median"
    if value <= p90:
        return "median_to_p90"
    return "above_p90"


def _supplier_benchmark_value(supplier: Dict[str, Any], metric: str, tco: TCOResult) -> float:
    """Pull the supplier's value for a given benchmark metric, in benchmark units.

    Implementation Fee benchmark is in '% of TCV' — we compute it from the
    flat fee and the (license + support) 3-year total.
    """
    if metric == "Price / User / Year":
        return float(supplier["net_price"])
    if metric == "Implementation Fee":
        tcv = tco.license_total + tco.support_total
        if tcv <= 0:
            return 0.0
        return float(supplier["implementation_fee"]) / tcv * 100.0
    if metric == "Annual Support":
        return float(supplier["support_pct"])
    if metric == "Uptime SLA":
        return float(supplier["uptime_sla_pct"])
    if metric == "SLA Credit":
        return float(supplier["sla_credit_pct"])
    if metric == "Termination for Convenience":
        return float(supplier["termination_notice_days"])
    raise KeyError(f"Unknown benchmark metric: {metric}")


# ---------------------------------------------------------------------------
# Findings: TCO
# ---------------------------------------------------------------------------

def compute_tco(supplier: Dict[str, Any], context: SourcingContext) -> TCOResult:
    """Compute 3-year TCO for FY-2025 through FY-2027.

    For each fiscal year:
      - Look up forecasted seats from context.usage
      - Determine tier band from seat count
      - license = net_price × seats
      - support = license × support_pct / 100
    """
    net_price = float(supplier["net_price"])
    support_pct = float(supplier["support_pct"])
    implementation = float(supplier.get("implementation_fee", 0.0))

    year_breakdown: List[Dict[str, Any]] = []
    license_total = 0.0
    support_total = 0.0

    for fy in CONTRACT_FISCAL_YEARS:
        seats = _seats_for_fy(context, fy)
        tier = _tier_for_seats(seats)
        license_amt = net_price * seats
        support_amt = license_amt * support_pct / 100.0
        year_breakdown.append({
            "fy": fy,
            "seats": seats,
            "tier": tier,
            "net_price": net_price,
            "license": round(license_amt, 2),
            "support": round(support_amt, 2),
        })
        license_total += license_amt
        support_total += support_amt

    total_3yr_tco = license_total + support_total + implementation

    return TCOResult(
        year_breakdown=year_breakdown,
        total_3yr_tco=round(total_3yr_tco, 2),
        license_total=round(license_total, 2),
        support_total=round(support_total, 2),
        implementation=round(implementation, 2),
    )


# ---------------------------------------------------------------------------
# Findings: Benchmark deltas
# ---------------------------------------------------------------------------

def benchmark_delta(supplier: Dict[str, Any], context: SourcingContext) -> List[Dict[str, Any]]:
    """For each of the 6 benchmark metrics, return supplier vs benchmark.

    Returns a list of dicts: {metric, supplier_value, p10, median, p90, position, unit}.
    """
    # We need TCO for the implementation-fee % calc.
    tco = compute_tco(supplier, context)

    results: List[Dict[str, Any]] = []
    for b in context.benchmarks:
        supplier_value = _supplier_benchmark_value(supplier, b.metric, tco)
        position = _classify_position(supplier_value, b.p10, b.median, b.p90)
        results.append({
            "metric": b.metric,
            "supplier_value": round(supplier_value, 4),
            "p10": b.p10,
            "median": b.median,
            "p90": b.p90,
            "unit": b.unit,
            "position": position,
        })
    return results


# ---------------------------------------------------------------------------
# Findings: Budget envelope check
# ---------------------------------------------------------------------------

def budget_envelope_check(tco_result: TCOResult, context: SourcingContext) -> Dict[str, Any]:
    """Compare TCO requirements against FP&A budget envelopes."""
    per_fy: List[Dict[str, Any]] = []
    total_required = 0.0
    total_available = 0.0

    for year in tco_result.year_breakdown:
        fy = year["fy"]
        required = year["license"] + year["support"]
        envelope = _budget_for_fy(context, fy)
        if envelope is None:
            available = 0.0
        else:
            available = envelope.license_budget + envelope.support_budget
        delta = available - required
        per_fy.append({
            "fy": fy,
            "required": round(required, 2),
            "available": round(available, 2),
            "delta": round(delta, 2),
            "over_budget": required > available,
        })
        total_required += required
        total_available += available

    return {
        "per_fy": per_fy,
        "total_3yr_required": round(total_required, 2),
        "total_3yr_available": round(total_available, 2),
        "total_3yr_delta": round(total_available - total_required, 2),
        "over_budget_3yr": total_required > total_available,
    }


# ---------------------------------------------------------------------------
# Findings: Integration coverage
# ---------------------------------------------------------------------------

def integration_coverage(supplier: Dict[str, Any], context: SourcingContext) -> List[Dict[str, Any]]:
    """Stub coverage check — returns claimed-but-unverified status for each dep.

    Future: parse supplier['extracted_terms'] to verify each dependency.
    """
    _ = supplier  # placeholder for future use
    return [
        {
            "dep_id": dep.dep_id,
            "status": "Capability claimed -- verification required",
            "criticality": dep.criticality,
        }
        for dep in context.integrations
    ]


# ---------------------------------------------------------------------------
# Findings: Exit cost at end of year 1
# ---------------------------------------------------------------------------

def exit_cost_year2(supplier: Dict[str, Any], context: SourcingContext) -> float:
    """Cost of terminating at end of Year 1 (two years remaining).

    For percentage-of-TCV formulas, remaining TCV = sum of license + support
    for FY-2026 and FY-2027.
    """
    penalty = supplier.get("termination_penalty") or {"type": "none", "value": 0}
    ptype = penalty.get("type", "none")

    if ptype == "none":
        return 0.0

    if ptype == "fixed":
        return float(penalty.get("value", 0.0))

    if ptype == "pct_of_remaining_tcv":
        tco = compute_tco(supplier, context)
        # Years remaining are FY-2026 and FY-2027 (skip FY-2025, which is year 1)
        remaining = 0.0
        for year in tco.year_breakdown:
            if year["fy"] in ("FY-2026", "FY-2027"):
                remaining += year["license"] + year["support"]
        return round(float(penalty.get("value", 0.0)) / 100.0 * remaining, 2)

    raise ValueError(f"Unknown termination_penalty type: {ptype}")


# ---------------------------------------------------------------------------
# Findings: Hidden risks (heuristic rules)
# ---------------------------------------------------------------------------

def _has_soc2_type_ii(certs: List[str]) -> bool:
    return any("soc 2 type ii" in str(c).lower() for c in certs or [])


def _is_single_region(data_residency: str) -> bool:
    text = (data_residency or "").lower()
    return "single-region" in text or "single region" in text


def _forecast_crosses_tier_breakpoint(context: SourcingContext) -> bool:
    """True if the forecasted seat count crosses a tier breakpoint within the contract term."""
    tiers = []
    for fy in CONTRACT_FISCAL_YEARS:
        seats = _seats_for_fy(context, fy)
        tiers.append(_tier_for_seats(seats))
    return len(set(tiers)) > 1


def surface_hidden_risks(
    supplier: Dict[str, Any],
    tco: TCOResult,
    bench: List[Dict[str, Any]],
    exit_cost: float,
) -> List[Dict[str, Any]]:
    """Apply heuristic rules and return a list of risk findings."""
    supplier_name = supplier.get("supplier_name", "Unknown")
    bench_by_metric = {row["metric"]: row for row in bench}

    risks: List[Dict[str, Any]] = []

    # Rule 1: Termination penalty > $200K → high-severity exit risk
    if exit_cost > 200_000:
        risks.append({
            "severity": "high",
            "headline": "Significant exit cost: termination penalty exceeds $200K threshold",
            "dollar_impact": round(exit_cost, 2),
            "supporting_evidence": (
                f"Termination at end of Year 1 would cost ${exit_cost:,.0f}, "
                f"limiting strategic flexibility. Penalty formula: "
                f"{supplier.get('termination_penalty')}."
            ),
            "supplier_name": supplier_name,
        })

    # Rule 2: Lacks SOC 2 Type II AND single-region data residency → high-severity compliance gap
    if not _has_soc2_type_ii(supplier.get("certs", [])) and _is_single_region(
        supplier.get("data_residency", "")
    ):
        risks.append({
            "severity": "high",
            "headline": "Compliance gap: missing SOC 2 Type II and single-region data residency",
            "dollar_impact": 0.0,
            "supporting_evidence": (
                f"Certifications listed: {supplier.get('certs', [])}. "
                f"Data residency: {supplier.get('data_residency', 'N/A')}. "
                "Both an enterprise compliance baseline (SOC 2 Type II) and "
                "geographic redundancy are missing."
            ),
            "supplier_name": supplier_name,
        })

    # Rule 3: Implementation fee below P10 → medium-positive (commercial flexibility signal)
    impl_row = bench_by_metric.get("Implementation Fee")
    if impl_row and impl_row["position"] == "below_p10":
        risks.append({
            "severity": "medium-positive",
            "headline": "Implementation fee below P10 -- vendor signaling commercial flexibility",
            "dollar_impact": round(tco.implementation, 2),
            "supporting_evidence": (
                f"Implementation fee is {impl_row['supplier_value']:.2f}% of TCV, "
                f"below the P10 benchmark of {impl_row['p10']}%. "
                "Use as a leverage point in broader negotiation."
            ),
            "supplier_name": supplier_name,
        })

    # Rule 4: Support % at or above P90 → medium-negative (recurring cost inflation)
    support_row = bench_by_metric.get("Annual Support")
    if support_row and support_row["supplier_value"] >= support_row["p90"]:
        annual_support_excess = (
            (support_row["supplier_value"] - support_row["median"]) / 100.0 * tco.license_total / 3.0
        )
        risks.append({
            "severity": "medium-negative",
            "headline": "Annual support fee at/above P90 -- recurring cost inflation",
            "dollar_impact": round(annual_support_excess, 2),
            "supporting_evidence": (
                f"Support % is {support_row['supplier_value']:.1f}%, at/above the P90 "
                f"benchmark of {support_row['p90']}%. Drives roughly "
                f"${annual_support_excess:,.0f}/yr more than median."
            ),
            "supplier_name": supplier_name,
        })

    # Rule 5: Forecast crosses tier breakpoint within contract term → medium-opportunity
    if _forecast_crosses_tier_breakpoint(AIRBNB_CONTEXT_FOR_RULE5(supplier, tco)):
        risks.append({
            "severity": "medium-opportunity",
            "headline": "Forecast crosses tier breakpoint -- negotiation lever available",
            "dollar_impact": 0.0,
            "supporting_evidence": (
                "Seat forecast spans more than one pricing tier across "
                "FY-2025 / FY-2026 / FY-2027. Negotiate locked tier-1 or "
                "tier-2 pricing through end of contract term."
            ),
            "supplier_name": supplier_name,
        })

    # Rule 6: Uptime SLA at or below P10 → high-severity reliability gap
    uptime_row = bench_by_metric.get("Uptime SLA")
    if uptime_row and uptime_row["supplier_value"] <= uptime_row["p10"]:
        risks.append({
            "severity": "high",
            "headline": "Uptime SLA at/below P10 -- reliability gap",
            "dollar_impact": 0.0,
            "supporting_evidence": (
                f"Uptime SLA is {uptime_row['supplier_value']}%, at/below the P10 "
                f"benchmark of {uptime_row['p10']}%. Insufficient for production-"
                "critical workloads without significantly higher SLA credits."
            ),
            "supplier_name": supplier_name,
        })

    return risks


def AIRBNB_CONTEXT_FOR_RULE5(supplier, tco):
    # Helper indirection so the rule can be re-pointed at any context.
    # Rule 5 actually only needs the forecast — which in this prototype is
    # always the canonical AIRBNB_CONTEXT singleton.
    _ = supplier, tco
    return AIRBNB_CONTEXT


# ---------------------------------------------------------------------------
# Top-level wrapper
# ---------------------------------------------------------------------------

def run_all_findings(supplier: Dict[str, Any], context: SourcingContext) -> Dict[str, Any]:
    """Run every finding function and return a consolidated dict."""
    tco = compute_tco(supplier, context)
    bench = benchmark_delta(supplier, context)
    budget = budget_envelope_check(tco, context)
    integration = integration_coverage(supplier, context)
    exit_cost = exit_cost_year2(supplier, context)
    hidden_risks = surface_hidden_risks(supplier, tco, bench, exit_cost)

    return {
        "supplier_name": supplier.get("supplier_name", "Unknown"),
        "tco": tco.to_dict(),
        "benchmarks": bench,
        "budget": budget,
        "integration": integration,
        "exit_cost": exit_cost,
        "hidden_risks": hidden_risks,
    }


# ---------------------------------------------------------------------------
# Sample fixtures (AlphaBI / BeaconIQ / DataNova)
#
# These are temporary test fixtures matching the schema expected by this
# engine. When Prompt 3 (which formally defines supplier dicts) lands,
# these can be moved or replaced.
# ---------------------------------------------------------------------------

SAMPLE_SUPPLIERS: Dict[str, Dict[str, Any]] = {
    "AlphaBI": {
        "supplier_name": "AlphaBI",
        "net_price": 250.0,
        "support_pct": 12.0,
        "implementation_fee": 50_000.0,
        "uptime_sla_pct": 99.95,
        "sla_credit_pct": 12.0,
        "termination_notice_days": 60,
        "termination_penalty": {"type": "fixed", "value": 300_000.0},
        "certs": ["SOC 2 Type II", "ISO 27001"],
        "data_residency": "multi-region",
    },
    "BeaconIQ": {
        "supplier_name": "BeaconIQ",
        "net_price": 230.0,
        "support_pct": 25.0,
        "implementation_fee": 100_000.0,
        "uptime_sla_pct": 99.0,
        "sla_credit_pct": 10.0,
        "termination_notice_days": 90,
        "termination_penalty": {"type": "fixed", "value": 100_000.0},
        "certs": ["ISO 27001"],
        "data_residency": "single-region (us-east-1)",
    },
    "DataNova": {
        "supplier_name": "DataNova",
        "net_price": 220.0,
        "support_pct": 18.0,
        "implementation_fee": 25_000.0,
        "uptime_sla_pct": 99.9,
        "sla_credit_pct": 15.0,
        "termination_notice_days": 30,
        "termination_penalty": {"type": "none", "value": 0.0},
        "certs": ["SOC 2 Type II", "ISO 27001"],
        "data_residency": "multi-region",
    },
}
