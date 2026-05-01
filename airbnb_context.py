"""Airbnb organizational sourcing context — single source of truth.

Holds industry benchmarks, usage forecasts, FP&A budget envelopes, and
integration dependencies. Consumed by the UI, the deterministic scoring
engine, and injected into LLM prompts via ``to_prompt_context()``.

Usage::

    from airbnb_context import AIRBNB_CONTEXT
    print(AIRBNB_CONTEXT.benchmarks[0].metric)
    AIRBNB_CONTEXT.update_budget("FY-2026", 950_000)
    prompt_block = AIRBNB_CONTEXT.to_prompt_context()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IndustryBenchmark:
    """A single industry benchmark distribution (p10 / median / p90)."""

    metric: str
    p10: float
    median: float
    p90: float
    unit: str


@dataclass
class UsageForecast:
    """Forecasted seat count for a fiscal year."""

    fiscal_year: str
    expected_seats: int
    yoy_growth_pct: Optional[float]
    notes: str


@dataclass
class BudgetEnvelope:
    """FP&A budget envelope for a fiscal year."""

    fiscal_year: str
    license_budget: float
    implementation_pool: Optional[float]
    support_budget: float


@dataclass
class IntegrationDependency:
    """A required integration with its owner and target deadline."""

    dep_id: str
    description: str
    criticality: str
    owner: str
    target_deadline: str


# ---------------------------------------------------------------------------
# Raw data (single source of truth)
# ---------------------------------------------------------------------------

INDUSTRY_BENCHMARKS = [
    ("Price / User / Year", 210, 250, 310, "$"),
    ("Implementation Fee", 3, 6, 12, "% of TCV"),
    ("Annual Support", 15, 20, 25, "% of License"),
    ("Uptime SLA", 99.5, 99.9, 99.99, "%"),
    ("SLA Credit", 8, 12, 18, "% of MRR"),
    ("Termination for Convenience", 30, 60, 120, "days"),
]

USAGE_FORECAST = [
    ("FY-2024", 2500, None, "Go-live in Q3, baseline"),
    ("FY-2025", 3400, 36.0, "Product & Growth org expansion"),
    ("FY-2026", 4200, 24.0, "International rollout"),
    ("FY-2027", 5000, 19.0, "Steady-state trajectory"),
]

FPNA_BUDGET = [
    ("FY-2024", 650000, 120000, 110000),
    ("FY-2025", 850000, None, 150000),
    ("FY-2026", 1000000, None, 180000),
    ("FY-2027", 1200000, None, 210000),
]

INTEGRATION_DEPENDENCIES = [
    ("INT-SSO", "SSO via Okta with SCIM provisioning", "High", "Identity Eng", "Q2 2024"),
    ("INT-LDS", "Data Lakehouse connector (Snowflake)", "High", "Data Eng", "Q3 2024"),
    (
        "INT-RBAC",
        "Role-Based Access Controls (granular scopes)",
        "Medium",
        "Security Eng",
        "Q3 2024",
    ),
    (
        "INT-API",
        "Streaming API for near-real-time dashboards",
        "Low",
        "Platform Eng",
        "Q1 2025",
    ),
]


# ---------------------------------------------------------------------------
# Helpers for the prompt-context formatter
# ---------------------------------------------------------------------------

def _fmt_money(value: float) -> str:
    """Format a USD value compactly: 950000 -> $950K, 1200000 -> $1.2M."""
    if value >= 1_000_000:
        millions = value / 1_000_000
        if millions == int(millions):
            return f"${int(millions)}M"
        return f"${millions:.1f}M"
    if value >= 1_000:
        thousands = value / 1_000
        if thousands == int(thousands):
            return f"${int(thousands)}K"
        return f"${thousands:.1f}K"
    return f"${value:,.0f}"


def _fmt_num(value: float) -> str:
    """Format a number, dropping trailing .0 for integers."""
    if value == int(value):
        return str(int(value))
    return str(value)


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

@dataclass
class SourcingContext:
    """Aggregate sourcing context — all four datasets in one place."""

    benchmarks: List[IndustryBenchmark]
    usage: List[UsageForecast]
    budget: List[BudgetEnvelope]
    integrations: List[IntegrationDependency]

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def default(cls) -> "SourcingContext":
        """Return a populated instance using the module-level constants."""
        return cls(
            benchmarks=[IndustryBenchmark(*row) for row in INDUSTRY_BENCHMARKS],
            usage=[UsageForecast(*row) for row in USAGE_FORECAST],
            budget=[BudgetEnvelope(*row) for row in FPNA_BUDGET],
            integrations=[IntegrationDependency(*row) for row in INTEGRATION_DEPENDENCIES],
        )

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def update_budget(self, fiscal_year: str, license_budget: float) -> None:
        """Update the license budget for one fiscal year, in place.

        Raises:
            ValueError: if ``fiscal_year`` is not present in ``self.budget``.
        """
        for envelope in self.budget:
            if envelope.fiscal_year == fiscal_year:
                envelope.license_budget = license_budget
                return
        raise ValueError(f"Fiscal year {fiscal_year} not found")

    # ------------------------------------------------------------------
    # Prompt formatting
    # ------------------------------------------------------------------

    def to_prompt_context(self) -> str:
        """Return a compact markdown summary suitable for LLM prompt injection.

        Target length: under 1500 characters.
        """
        lines: List[str] = []
        lines.append("### Airbnb Sourcing Context")
        lines.append("")

        # --- Benchmarks ---
        lines.append("**Industry Benchmarks** (p10 / median / p90)")
        for b in self.benchmarks:
            unit = b.unit
            if unit == "$":
                vals = f"${_fmt_num(b.p10)} / ${_fmt_num(b.median)} / ${_fmt_num(b.p90)}"
            else:
                vals = f"{_fmt_num(b.p10)} / {_fmt_num(b.median)} / {_fmt_num(b.p90)} {unit}"
            lines.append(f"- {b.metric}: {vals}")
        lines.append("")

        # --- Usage forecast ---
        lines.append("**Usage Forecast**")
        for u in self.usage:
            seats = f"{u.expected_seats:,} seats"
            growth = f" (+{u.yoy_growth_pct:.0f}% YoY)" if u.yoy_growth_pct is not None else " (baseline)"
            lines.append(f"- {u.fiscal_year}: {seats}{growth}")
        lines.append("")

        # --- Budget ---
        lines.append("**FP&A Budget**")
        for envelope in self.budget:
            parts = [f"License {_fmt_money(envelope.license_budget)}"]
            if envelope.implementation_pool is not None:
                parts.append(f"Impl {_fmt_money(envelope.implementation_pool)}")
            parts.append(f"Support {_fmt_money(envelope.support_budget)}")
            lines.append(f"- {envelope.fiscal_year}: {', '.join(parts)}")
        lines.append("")

        # --- Integrations ---
        lines.append("**Integration Dependencies**")
        for dep in self.integrations:
            lines.append(
                f"- {dep.dep_id} ({dep.criticality}, {dep.owner}, {dep.target_deadline}): "
                f"{dep.description}"
            )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

AIRBNB_CONTEXT = SourcingContext.default()
