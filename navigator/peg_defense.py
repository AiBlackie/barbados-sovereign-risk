# navigator/peg_defense.py

import json

class PegDefenseMonitor:
    def __init__(self, state_file="data/sovereign_state.json"):
        with open(state_file, "r") as f:
            self.state = json.load(f)
        self.gdp = self.state["nominal_gdp"]
        hidden = self.state["hidden_liabilities"]
        
        # Calculate total parliamentary resolutions
        parl_res = hidden.get("parliamentary_resolutions_2022_2025", {})
        total_parl = sum(parl_res.values())

        # The Core Formula
        self.true_debt = (
            self.state["official_debt"]["central_govt"] +
            hidden.get("cbb_negative_equity", 0) +
            hidden.get("nis_unfunded_actuarial_shortfall", 0) +
            hidden.get("govt_pension_unfunded_liability", 0) +
            hidden.get("soe_arrears", 0) +
            hidden.get("soe_non_guaranteed_debt", 0) +
            total_parl
        )

    def analyze(self):
        ext = self.state["external_sector"]
        
        reserves = ext["gross_reserves"]
        weeks_cover = ext["weeks_of_import_cover"]
        cad = ext["current_account_deficit_annual"]
        fdi = ext["fdi_inflows_annual"]
        cbb_neg_eq = self.state["hidden_liabilities"].get("cbb_negative_equity", 0)

        # 1. Baseline Net Burn Rate
        net_burn = cad - fdi 
        
        # 2. Timeline to 12-Week Benchmark
        weekly_imports = reserves / weeks_cover
        target_reserves = weekly_imports * 12
        
        if net_burn > 0:
            if reserves <= target_reserves:
                months_to_danger = 0
                alert = "IMMINENT: Reserves are already below the 12-week benchmark."
            else:
                months_to_danger = ((reserves - target_reserves) / net_burn) * 12
                alert = f"COUNTDOWN: At current burn rate, reserves will hit the 12-week benchmark in {months_to_danger:.1f} months."
        else:
            months_to_danger = float('inf')
            alert = "STABLE: Foreign inflows are covering the current account deficit."

        # --- NEW SCORING MODEL ---
        
        # Component 1: Reserve Adequacy Risk (30% weight)
        if weeks_cover >= 40: reserve_risk = 0
        elif weeks_cover <= 12: reserve_risk = 70 + ((12 - weeks_cover) / 12) * 30
        else: reserve_risk = ((40 - weeks_cover) / 28) * 70

        # Component 2: Central Bank Insolvency Risk (40% weight)
        insolvency_ratio = (cbb_neg_eq / reserves) * 100
        insolvency_risk = min(100, insolvency_ratio)

        # Component 3: Macro Debt Risk (30% weight)
        true_debt_ratio = (self.true_debt / self.gdp) * 100
        if true_debt_ratio <= 60: debt_risk = 0
        elif true_debt_ratio >= 160: debt_risk = 100
        else: debt_risk = ((true_debt_ratio - 60) / 100) * 100

        # Final Weighted Score
        peg_score = (reserve_risk * 0.30) + (insolvency_risk * 0.40) + (debt_risk * 0.30)
        peg_score = min(100, max(0, peg_score))

        return {
            "net_burn_rate_bds": net_burn,
            "insolvency_ratio_pct": round(insolvency_ratio, 1),
            "months_to_12_week_benchmark": round(months_to_danger, 1) if months_to_danger != float('inf') else "N/A",
            "peg_vulnerability_score": round(peg_score, 1),
            "alert": alert,
            "score_breakdown": {
                "Reserve Risk": round(reserve_risk, 1),
                "CBB Insolvency Risk": round(insolvency_risk, 1),
                "Macro Debt Risk": round(debt_risk, 1)
            }
        }