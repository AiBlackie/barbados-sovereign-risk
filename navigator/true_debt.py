# navigator/true_debt.py

import json
import os

class TrueDebtCalculator:
    def __init__(self, state_file="data/sovereign_state.json"):
        with open(state_file, "r") as f:
            self.state = json.load(f)

    def calculate(self):
        gdp = self.state["nominal_gdp"]
        official_debt = self.state["official_debt"]["central_govt"]
        
        hidden = self.state["hidden_liabilities"]
        cbb_neg_eq = hidden["cbb_negative_equity"]
        nis_shortfall = hidden["nis_unfunded_actuarial_shortfall"]
        govt_pension = hidden["govt_pension_unfunded_liability"]
        soe_arrears = hidden["soe_arrears"]
        soe_debt = hidden.get("soe_non_guaranteed_debt", 0)
        
        # Parliamentary Resolutions (2022-2025)
        parl_res = hidden.get("parliamentary_resolutions_2022_2025", {})
        total_parl = sum(parl_res.values())

        # The Core Formula (expanded, with 2013 QEH/RBC loan excluded)
        true_debt = (official_debt + cbb_neg_eq + nis_shortfall 
                     + govt_pension + soe_arrears + soe_debt 
                     + total_parl)
        hidden_gap = true_debt - official_debt

        # Ratios
        official_ratio = (official_debt / gdp) * 100
        true_ratio = (true_debt / gdp) * 100

        # Traffic Light
        if true_ratio >= 100:
            status = "CRITICAL: Debt is unsustainable. High probability of default or restructuring."
        elif true_ratio >= 60:
            status = "WARNING: Debt exceeds international sustainability benchmarks."
        else:
            status = "SAFE: Within acceptable limits."

        # --- FORENSIC EVIDENCE ---
        evidence = {
            "parliamentary_resolutions": {
                "quote": "WHEREAS by virtue of section 2 of the Special Loans Act, Cap. 105, the Government is authorised from time to time to borrow... The nine Parliamentary Resolutions from 2022-2025 authorise total borrowing of approximately BBD $1.48 billion and USD $37.4 million.",
                "source": "Parliamentary Resolutions (2022-2025), Special Loans Act, Cap. 105"
            },
            "qeh_rbc_loan_excluded": {
                "quote": "The QEH RBC loan (BDS $25M, 2013 Resolution) is excluded from this register. The loan carried a 7-year term from disbursement, implying maturity around 2020-2021. There is no evidence of extension or refinancing in the 2025-2026 documentation.",
                "source": "Parliamentary Resolution, December 5, 2013 (Page 3, Terms and Conditions)"
            },
            "imf_disclosure": {
                "quote": "Figure 1. Barbados: Debt Coverage and Disclosure. NIS (Social security funds): Not consolidated. Central Bank: Not consolidated.",
                "source": "IMF 2026 Article IV Consultation, Annex II, Figure 1 (Page 58)"
            },
            "imf_dsa_boundary": {
                "quote": "SOE debt not guaranteed by the central government is small at 2.6 percent of GDP at end-March 2026 and is not included in the analysis.",
                "source": "IMF 2026 Article IV, Annex II, Footnote 1 (Page 57)"
            },
            "imf_contingent_liabilities": {
                "quote": "Contingent liabilities: 147.2 (1.9% of GDP)... of which Public guarantees: 147.2 (1.9% of GDP)",
                "source": "IMF 2026 Article IV, Annex II, Table 2 (Page 62)"
            },
            "imf_nis_assessment": {
                "quote": "The parametric changes between 2022 and 2023... are expected to make the National Insurance Scheme financially sustainable for 25-30 years... The increase in pension benefits... is expected to peak by the mid-2050s.",
                "source": "IMF 2026 Article IV, Annex II, Figure 6 (Page 60)"
            },
            "imf_srdsf_assessment": {
                "quote": "The Sovereign Risk and Debt Sustainability Framework (SRDSF) suggests that Barbados' overall risk of sovereign stress is moderate, and that debt is sustainable (see Annex II).",
                "source": "IMF 2026 Article IV, ¶22 (Page 24)"
            },
            "parliamentary_resolution_2025": {
                "quote": "WHEREAS the Government of Barbados deems it necessary to borrow up to $500 million in the currency of the United States of America on the international capital market the proceeds of which will be used to fund the liability management operation and to prepay a portion of Central Government's debt to the International Monetary Fund for the External Fund Facility... Coupon: 8.000 per cent per annum... Maturity: 26th June, 2035",
                "source": "Parliamentary Resolution, June 24, 2025 (Pages 1 & 4)"
            },
            "cbb_negative_equity": {
                "quote": "The Bank has recorded net capital and deficit of $1,422,167 [thousands] (2024: $1,528,756 [thousands]) as at December 31, 2025... A recapitalization plan for the CBB remains in place... rebuilding capital through profit retention.",
                "source": "CBB 2025 Annual Report, Note 1 (Page 70) & IMF 2026 Article IV (Page 25, ¶27)"
            },
            "nis_shortfall": {
                "quote": "Total Net Assets: $4,234M. ...Reserves are projected to be exhausted in 2036. IMF 2026: parametric reforms are expected to make the NISSS financially sustainable for 25-30 years, with a residual financing need of 0.2-0.4 pp of GDP per year for 50 years.",
                "source": "NIS 17th Actuarial Review (Page 16) & IMF 2026 Article IV (Page 60, Figure 6)"
            },
            "govt_pension_liability": {
                "quote": "In addition, the liability for pensions and employee benefits were not included in the Statement of Financial Position... The Government of Barbados uses an unfunded defined benefit plan... No assets are therefore being put aside.",
                "source": "Auditor General Report 2023, Page 4 (Basis for Adverse Opinion) & Note 8 (Page 23)"
            },
            "soe_debt": {
                "quote": "Government guaranteed SOE debt remained contained at BDS $69.8 million at end-March 2026 (0.4 percent of GDP). SOE non-guaranteed debt also remains stable at around BDS $426 million (2.7 percent of GDP). Implicit government guarantees remain a concern, including unfunded pension liabilities.",
                "source": "IMF 2026 Article IV Consultation, Annex VII (Page 87, ¶5)"
            },
            "soe_arrears": {
                "quote": "At the end of August 2025, total SOE arrears stood at $74.6 million... roughly 78 per cent is concentrated at the National Petroleum Corporation, the Barbados Water Authority, and the Sanitation Service Authority.",
                "source": "Ministry of Finance Mid-Year Review 2025, Section 4.3 (Page 22)"
            }
        }

        return {
            "official_debt_bds": official_debt,
            "hidden_gap_bds": hidden_gap,
            "true_debt_bds": true_debt,
            "official_ratio_pct": round(official_ratio, 1),
            "true_ratio_pct": round(true_ratio, 1),
            "status": status,
            "hidden_gap_breakdown": hidden,
            "forensic_evidence": evidence,
            "total_parl_resolutions": total_parl
        }