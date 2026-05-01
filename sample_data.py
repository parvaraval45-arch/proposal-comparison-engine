"""Sample supplier proposals for the Proposal Comparison Engine demo.

Scenario: Data & Analytics Platform Renewal -- 3-Year Software Agreement.
Three vendors with contrasting commercial profiles (AlphaBI, BeaconIQ,
DataNova) so the deterministic engine can surface the specific gotchas
the AI should catch.

Each proposal carries both:

* ``proposal_text`` -- the narrative the LLM extracts from
* ``structured_data`` -- the canonical fields the deterministic engine reads

Both must agree. If you edit one, edit the other.
"""

SAMPLE_PROPOSALS = {
    "scenario_name": "Data & Analytics Platform Renewal -- 3-Year Software Agreement",
    "scenario_description": (
        "Airbnb is selecting a Data & Analytics platform serving the Product, "
        "Growth, and International orgs. Annual seat forecast ramps from 2,500 "
        "in FY-24 to 5,000 in FY-27. The agreement is a 3-year term with a "
        "forecasted 3-year TCV in the $3M-$4M range. Three vendors with "
        "contrasting commercial profiles have been evaluated: AlphaBI (mature "
        "enterprise incumbent), BeaconIQ (challenger with attractive headline "
        "pricing but compliance gaps), and DataNova (modern, premium-priced, "
        "highest flexibility)."
    ),
    "proposals": [
        # ──────────────────────────────────────────────────────────────────
        # 1. ALPHABI
        # ──────────────────────────────────────────────────────────────────
        {
            "supplier_name": "AlphaBI",
            "proposal_text": (
                "PROPOSAL FOR DATA & ANALYTICS PLATFORM SUBSCRIPTION\n"
                "Submitted to: Airbnb, Inc.\n"
                "Submitted by: AlphaBI Corporation\n"
                "Term: 3-year software agreement\n\n"

                "1. COMPANY OVERVIEW\n\n"
                "AlphaBI is a market-leading enterprise data and analytics platform "
                "trusted by more than 600 enterprise customers across financial "
                "services, retail, healthcare, and consumer technology. Our platform "
                "covers ingestion, transformation, semantic modeling, governed BI, "
                "and embedded analytics in a single subscription. We have a 12-year "
                "operating history, 1,400 employees globally, and a delivery footprint "
                "in North America, EMEA, and APAC. AlphaBI is recognized as a Leader "
                "in the most recent industry analyst evaluations of analytics and "
                "business-intelligence platforms, with consistent placement in the "
                "top quadrant on both ability-to-execute and completeness-of-vision "
                "axes for the past five evaluation cycles.\n\n"
                "Our customer base spans organizations from 500-seat departmental "
                "deployments to 25,000-seat enterprise rollouts. We bring deep "
                "experience integrating with the modern cloud data stack, including "
                "Snowflake, Databricks, BigQuery, and Redshift, and we maintain "
                "certified connectors and shared reference architectures for each.\n\n"

                "2. COMMERCIAL TERMS\n\n"
                "AlphaBI proposes a 3-year subscription priced on a per-named-user, "
                "per-year basis with three volume tiers:\n\n"
                "  Tier 1 (0-1K seats):  list $320/user/year, with a 10% volume "
                "discount, for a net price of $288/user/year.\n"
                "  Tier 2 (1K-5K seats): list $290/user/year, with a 15% volume "
                "discount, for a net price of $247/user/year.\n"
                "  Tier 3 (5K+ seats):   list $260/user/year, with a 22% volume "
                "discount, for a net price of $203/user/year.\n\n"
                "Tier banding is applied to the average seat count across the "
                "fiscal year, trued up at the end of each year. Pricing is locked "
                "for the full 3-year term subject to the standard CPI escalator "
                "capped at 3% per year. Volume discounts are non-stackable with "
                "additional rebates and are recognized only after the average seat "
                "count for the relevant fiscal year crosses the tier threshold.\n\n"
                "Implementation fee: $150,000 one-time, billed at contract signing. "
                "Includes onboarding, identity integration, semantic-layer migration, "
                "data-governance configuration, baseline dashboard migration, and "
                "8 weeks of dedicated solution-architect time. Additional weeks "
                "of solution-architect engagement are available at $2,500 per day "
                "T&M, with at least 10-business-day advance notice.\n\n"
                "Annual support: 18% of license. Includes 24x7 P1 coverage, a named "
                "Technical Account Manager, quarterly business reviews, access to "
                "the AlphaBI customer success portal, and unlimited access to our "
                "self-paced training curriculum. Support is delivered from regional "
                "centers in the US, Ireland, and Singapore to ensure follow-the-sun "
                "coverage for incidents.\n\n"

                "3. SERVICE LEVELS\n\n"
                "Uptime SLA: 99.9% measured monthly across the production tenant, "
                "excluding scheduled maintenance windows announced at least 7 "
                "business days in advance. SLA credit: 15% of monthly recurring "
                "revenue (MRR) for any month in which uptime falls below the "
                "99.9% commitment, capped at 50% of MRR per quarter. Credits are "
                "issued automatically against the next invoice and do not require "
                "Airbnb to file a claim.\n\n"

                "4. SECURITY, COMPLIANCE & DATA PRIVACY\n\n"
                "AlphaBI maintains the following certifications: SOC 2 Type II "
                "(audited annually with no exceptions in the past three audit "
                "cycles) and ISO 27001. Both reports are made available under NDA "
                "prior to contract signing. We support customer-managed encryption "
                "keys (BYOK) backed by AWS KMS, GCP KMS, or Azure Key Vault, full "
                "audit logging exportable to customer SIEMs, fine-grained "
                "role-based access, and SAML/SCIM provisioning via Okta, Azure AD, "
                "and Google Workspace. Penetration tests are conducted twice a "
                "year by an external CREST-certified vendor, and executive "
                "summaries are shared on request.\n\n"
                "Data residency options: US, EU, and APAC. Customers select the "
                "region of record at provisioning time, and AlphaBI guarantees "
                "that production tenant data, backups, and replicas remain inside "
                "the selected region. Cross-region failover is available within "
                "the same residency zone (for example, EU-West to EU-Central) "
                "without changing residency commitments.\n\n"

                "5. TERMINATION CLAUSE\n\n"
                "Either party may terminate this agreement with 90 days written "
                "notice. If Airbnb terminates for convenience prior to the end "
                "of the 3-year term, an early-termination penalty of 25% of "
                "remaining TCV is payable. Remaining TCV is defined as the sum "
                "of unbilled license and support fees for all years remaining in "
                "the contract term at the effective termination date. Termination "
                "for material breach is permitted with a 30-day cure period and "
                "no penalty.\n\n"

                "6. REFERENCES\n\n"
                "Salesforce (4,800 seats, 5-year customer), Cisco (3,200 seats), "
                "and Workday (2,500 seats). Reference contacts available on "
                "request following mutual NDA execution."
            ),
            "structured_data": {
                "term_years": 3,
                "tier_seats": ["0-1K", "1K-5K", "5K+"],
                "tier_list_price": [320, 290, 260],
                "tier_volume_discount_pct": [10, 15, 22],
                "tier_net_price": [288, 247, 203],
                "implementation_fee": 150_000,
                "annual_support_pct": 18,
                "uptime_sla": 99.9,
                "sla_credit_pct": 15,
                "data_privacy_certs": ["SOC 2 Type II", "ISO 27001"],
                "certs_caveat": None,
                "data_residency": ["US", "EU", "APAC"],
                "termination_notice_days": 90,
                "termination_penalty_formula": "25% of remaining TCV",
            },
        },

        # ──────────────────────────────────────────────────────────────────
        # 2. BEACONIQ
        # ──────────────────────────────────────────────────────────────────
        {
            "supplier_name": "BeaconIQ",
            "proposal_text": (
                "BEACONIQ PROPOSAL\n"
                "For: Airbnb, Inc.\n"
                "Subject: Data & Analytics Platform -- 3-Year Subscription\n\n"

                "1. ABOUT BEACONIQ\n\n"
                "BeaconIQ is a fast-growing data and analytics challenger founded "
                "in 2018, headquartered in Austin, TX, with engineering hubs in "
                "Toronto and Lisbon. We work with 180+ mid-market and emerging-"
                "enterprise customers and have raised Series C funding from a "
                "syndicate of leading enterprise-software investors. We pride "
                "ourselves on aggressive commercial flexibility, fast time-to-"
                "value implementations measured in weeks rather than quarters, "
                "and a clean, opinionated product surface that minimizes the "
                "configuration burden on customer engineering teams. Our average "
                "deployment goes from contract signature to first production "
                "dashboard in under 45 days.\n\n"
                "BeaconIQ's product is built on an open-source columnar engine, "
                "with proprietary semantic, governance, and orchestration layers "
                "above. We are well suited for analytics organizations that value "
                "iteration velocity and modern self-service workflows; we are "
                "less suited for federal or other heavily regulated workloads "
                "given our current compliance posture, which we transparently "
                "disclose below.\n\n"

                "2. COMMERCIAL TERMS\n\n"
                "BeaconIQ is offering a 3-year subscription with the following "
                "per-named-user, per-year pricing:\n\n"
                "  Tier 1 (0-1K seats):  list $350/user/year, 12% volume "
                "discount, net price $308/user/year.\n"
                "  Tier 2 (1K-5K seats): list $300/user/year, 18% volume "
                "discount, net price $246/user/year.\n"
                "  Tier 3 (5K+ seats):   list $275/user/year, 25% volume "
                "discount, net price $206/user/year.\n\n"
                "Tier banding is determined by average seats consumed in the "
                "trailing 12 months. List prices are reviewed annually; net "
                "prices are guaranteed only at signing for Year 1, and BeaconIQ "
                "reserves the right to revisit Year 2 and Year 3 net prices "
                "ahead of each renewal anniversary if there is a material change "
                "in market conditions or platform cost structure. Any uplift "
                "above 5% requires Airbnb consent, with a true-up reconciled at "
                "year end.\n\n"
                "Implementation fee: $95,000 one-time. Includes a 6-week "
                "deployment covering identity integration, two source-system "
                "connectors, and initial dashboard migration. Additional "
                "connectors are billed at T&M rates of $1,800 per day per "
                "implementation engineer. Custom semantic-model migration from "
                "legacy tools is in scope only for two source models; further "
                "migrations are quoted separately.\n\n"
                "Annual support: 22% of license. Includes 24x5 P1 coverage, "
                "shared support engineer, and access to the BeaconIQ customer "
                "community. 24x7 coverage and a named Technical Account Manager "
                "are available for an additional 6% of license uplift, billed "
                "annually.\n\n"

                "3. SERVICE LEVELS\n\n"
                "Uptime SLA: 99.5% measured monthly. SLA credit: 12% of monthly "
                "recurring revenue (MRR) per month of breach, capped at 30% of "
                "annual fees. Maintenance windows announced at least 5 business "
                "days in advance are excluded from the uptime calculation.\n\n"

                "4. SECURITY, COMPLIANCE & DATA PRIVACY\n\n"
                "BeaconIQ holds SOC 2 Type I attestation as of the most recent "
                "audit cycle. We are committed to completing a SOC 2 Type II "
                "audit; the Type II audit is scheduled for completion in 12 "
                "months. ISO 27001 is on the 24-month roadmap. We are not yet "
                "a CSA STAR registrant. We support encryption at rest and in "
                "transit, role-based access controls, and SAML SSO; customer-"
                "managed keys (BYOK) are on the roadmap but not generally "
                "available today.\n\n"
                "Data residency: US only. All BeaconIQ tenants are hosted in "
                "our us-east-1 region with cross-AZ replication. EU data "
                "residency is on the product roadmap but is not generally "
                "available at contract signing; an EU-Frankfurt region is "
                "targeted for general availability within 18 months. APAC "
                "residency is not on the current roadmap.\n\n"

                "5. TERMINATION CLAUSE\n\n"
                "Either party may terminate this agreement with 60 days "
                "written notice. If Airbnb terminates for convenience prior "
                "to the end of the 3-year term, an early-termination fee of "
                "15% of remaining TCV is payable. Remaining TCV is defined as "
                "the unbilled license and support fees for all years remaining "
                "in the term at the effective termination date.\n\n"

                "6. REFERENCES\n\n"
                "DoorDash (1,200 seats), Plaid (900 seats), and a Fortune 500 "
                "retailer who prefers to remain anonymous. Reference contacts "
                "available on request."
            ),
            "structured_data": {
                "term_years": 3,
                "tier_seats": ["0-1K", "1K-5K", "5K+"],
                "tier_list_price": [350, 300, 275],
                "tier_volume_discount_pct": [12, 18, 25],
                "tier_net_price": [308, 246, 206],
                "implementation_fee": 95_000,
                "annual_support_pct": 22,
                "uptime_sla": 99.5,
                "sla_credit_pct": 12,
                "data_privacy_certs": ["SOC 2 Type I"],
                "certs_caveat": "Type II audit scheduled for completion in 12 months",
                "data_residency": ["US"],
                "termination_notice_days": 60,
                "termination_penalty_formula": "15% of remaining TCV",
            },
        },

        # ──────────────────────────────────────────────────────────────────
        # 3. DATANOVA
        # ──────────────────────────────────────────────────────────────────
        {
            "supplier_name": "DataNova",
            "proposal_text": (
                "DATANOVA -- COMMERCIAL PROPOSAL\n"
                "Prepared for: Airbnb, Inc.\n"
                "Engagement: Data & Analytics Platform, 3-Year Software Agreement\n\n"

                "1. COMPANY OVERVIEW\n\n"
                "DataNova is a modern data and analytics platform built around "
                "an open-table semantic layer, governed self-service, and "
                "AI-assisted exploration. Founded in 2016, we serve 240+ "
                "customers including several global hyperscalers, leading "
                "consumer-internet brands, and US federal agencies. Our "
                "headcount is 950 employees across the US (Seattle HQ), "
                "Ireland (Dublin engineering), and Singapore (APAC support and "
                "field engineering). We are profitable on a free-cash-flow "
                "basis and reported $310M in ARR in our most recent fiscal "
                "year, growing at 42% year-over-year.\n\n"
                "DataNova is differentiated by three structural commitments: "
                "(a) a single composable platform rather than a suite of "
                "loosely integrated products; (b) open table formats (Iceberg, "
                "Delta) as a first-class storage substrate so customer data "
                "remains portable; and (c) a transparent commercial posture "
                "that emphasizes ease of exit. We believe customers should "
                "stay because the product is the best fit, not because the "
                "contract makes leaving expensive.\n\n"

                "2. COMMERCIAL TERMS\n\n"
                "DataNova offers a 3-year per-named-user subscription with the "
                "following tiering:\n\n"
                "  Tier 1 (0-1K seats):  list $400/user/year, 15% volume "
                "discount, net price $340/user/year.\n"
                "  Tier 2 (1K-5K seats): list $340/user/year, 20% volume "
                "discount, net price $272/user/year.\n"
                "  Tier 3 (5K+ seats):   list $300/user/year, 30% volume "
                "discount, net price $210/user/year.\n\n"
                "Pricing is locked for the full 3-year term with no CPI "
                "escalator and no list-price uplift on renewal anniversaries. "
                "Tier banding is calculated on average seats per fiscal year, "
                "trued up annually within 30 days of fiscal year close. "
                "Volume discounts are applied automatically once the average "
                "seat count crosses the next tier breakpoint.\n\n"
                "Implementation fee: $50,000 one-time. Reflects our "
                "standardized deployment toolkit and template-based migration "
                "accelerators. Includes identity integration, three connectors, "
                "4 weeks of implementation engineering, and a 30-day "
                "post-go-live hypercare period staffed by a senior solution "
                "architect. Additional connectors are included free of charge "
                "for any source system covered by the DataNova certified "
                "connector catalog.\n\n"
                "Annual support: 20% of license. Includes 24x7 P1 coverage, "
                "named Customer Success Manager, embedded Slack channel with "
                "our engineering team, quarterly architecture reviews, and "
                "unlimited admin-track training seats. Severity-1 issues "
                "carry a 15-minute response commitment with named-engineer "
                "callout.\n\n"

                "3. SERVICE LEVELS\n\n"
                "Uptime SLA: 99.95% measured monthly. SLA credit: 20% of "
                "monthly recurring revenue (MRR) per month of breach, with "
                "no aggregate cap. Credits are issued automatically and "
                "applied against the next invoice.\n\n"

                "4. SECURITY, COMPLIANCE & DATA PRIVACY\n\n"
                "DataNova holds SOC 2 Type II (audited annually with no "
                "exceptions) and is a registered processor under GDPR Article "
                "28 with executed Data Processing Addenda available "
                "pre-signing. FedRAMP Moderate is in process and expected by "
                "end of next fiscal year. We support customer-managed keys, "
                "BYOK with HSM backing in GovCloud, full audit-trail export "
                "to customer SIEMs, and field-level dynamic masking for "
                "PII/PHI workloads.\n\n"
                "Data residency: US, EU, and GovCloud. All three regions are "
                "production-grade and generally available today. The customer "
                "can designate region of record at provisioning, and DataNova "
                "guarantees that all production data, backups, and replicas "
                "remain inside the chosen region. Cross-region access for "
                "support purposes requires explicit written authorization "
                "from the customer's security organization.\n\n"

                "5. TERMINATION CLAUSE\n\n"
                "Either party may terminate this agreement with 30 days "
                "written notice. There is no fee after Year 1: if Airbnb "
                "terminates for convenience after the completion of the "
                "first contract year, no early-termination penalty is "
                "payable. Termination during Year 1 requires payment of "
                "remaining Year 1 fees only.\n\n"

                "6. REFERENCES\n\n"
                "Two Fortune 100 financial-services customers (under NDA), "
                "Snowflake (3,800 seats), and the US Department of Energy "
                "(GovCloud). Reference contacts available on request "
                "following mutual NDA execution. Each reference customer "
                "has been live on the DataNova platform for at least two "
                "years and is willing to discuss real-world deployment "
                "experience, including platform stability, support quality, "
                "and the practical mechanics of our termination terms."
            ),
            "structured_data": {
                "term_years": 3,
                "tier_seats": ["0-1K", "1K-5K", "5K+"],
                "tier_list_price": [400, 340, 300],
                "tier_volume_discount_pct": [15, 20, 30],
                "tier_net_price": [340, 272, 210],
                "implementation_fee": 50_000,
                "annual_support_pct": 20,
                "uptime_sla": 99.95,
                "sla_credit_pct": 20,
                "data_privacy_certs": ["SOC 2 Type II", "GDPR Article 28"],
                "certs_caveat": None,
                "data_residency": ["US", "EU", "GovCloud"],
                "termination_notice_days": 30,
                "termination_penalty_formula": "No fee after Year 1",
            },
        },
    ],
}
