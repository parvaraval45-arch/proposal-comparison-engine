# Supplier Proposal Comparison Engine

## The Problem

Sourcing teams manually review supplier proposals -- a process that is slow, inconsistent, and buries critical risks deep inside dense documents. At scale, a sourcing team evaluating dozens of proposals per quarter loses hundreds of analyst hours on term extraction and side-by-side comparison that could be spent on strategy and negotiation. The result is inconsistent evaluation quality, missed red flags, and negotiation leverage left on the table.

## The Solution

An AI-powered tool that extracts key commercial terms, scores suppliers against weighted strategic criteria, and generates a negotiation-ready brief in under 60 seconds. Built as a human-in-the-loop system -- AI structures the analysis, humans make the decisions. Every score includes transparent rationale so sourcing professionals can validate, adjust, and override before taking action.

## Where This Fits in the Sourcing Operating Model

- **Stage**: Post-RFP proposal evaluation -- after suppliers have submitted and before shortlist decisions
- **Users**: Sourcing analysts and category managers preparing evaluation summaries for leadership
- **Decisions informed**: Supplier shortlisting, negotiation strategy, and clarification round planning -- not final contract sign-off
- **Human validation required**: All AI-generated scores and recommendations must be reviewed by a sourcing professional before action

## How It Works

1. Upload or paste 2-3 supplier proposals
2. Adjust evaluation criteria weights to match your category priorities
3. AI extracts terms, scores proposals, compares suppliers, and generates a negotiation brief

## Sourcing Frameworks Applied

- **Total Cost of Ownership (TCO)** analysis -- looking beyond sticker price to flag hidden costs, change order markups, and price escalation clauses
- **Weighted multi-criteria evaluation** -- configurable by category, because what matters for IT sourcing differs from professional services
- **Risk-adjusted scoring** -- financial stability, key-person dependency, insurance adequacy, geographic concentration, and business continuity
- **BATNA-informed negotiation preparation** -- specific leverage points with concrete asks and expected impact
- **ESG and supplier diversity assessment** -- aligned with belonging-centered procurement values (MBE, WBE, LGBTBE, B Corp, carbon neutrality)

## Design Decisions

- Weights are category-dependent and intentionally user-controlled -- what matters for IT sourcing differs from professional services
- Recommendation based on weighted criteria; final decision should consider strategic context, relationship history, and factors beyond quantitative analysis
- All AI outputs include rationale transparency -- every score comes with an explanation
- SLA specificity is scored rigorously: vague commitments ("best effort") score lower than measurable guarantees ("99% on-time with 5% credit per incident")

## Limitations

- Prototype using synthetic data -- production deployment would require integration with CLM, SIM, and ERP systems
- Human-in-the-loop validation is essential -- AI extractions should be spot-checked against source documents
- Scoring calibration improves with domain-specific training data from historical evaluations
- Current version optimized for indirect spend categories (services, technology, consulting)

## Built For

Airbnb Sourcing Operations & Innovation Intern (MBA) application -- demonstrating AI-augmented sourcing judgment at the intersection of strategy, operating model design, and AI enablement.

## Tech Stack

- Streamlit + Anthropic Claude API (Sonnet)
- Plotly for data visualization
- fpdf2 for PDF report generation

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key  # or enter in the app sidebar
streamlit run app.py
```
