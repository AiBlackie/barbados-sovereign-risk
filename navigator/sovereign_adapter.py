# navigator/sovereign_adapter.py
"""
Sovereign Adapter v2.0
Bridges the GFTI Forensic Extraction (app.py/extractor.py) with the 
Sovereign Risk Navigator (true_debt.py/report_generator.py).

Entity-aware: handles Central Government, Central Bank, and SOE statements differently.
Each liability is resolved from (in order):
  1. Direct extraction from the uploaded PDF
  2. Documented fallback (with a clear _provenance trail)
"""

import json
from pathlib import Path


def _safe_num(val, default=0.0):
    if val is None: return default
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        cleaned = val.replace(",", "").replace(" ", "").strip()
        for sym in ["$", "BDS", "USD", "M"]: cleaned = cleaned.replace(sym, "")
        is_paren = cleaned.startswith("(") and cleaned.endswith(")")
        if is_paren: cleaned = cleaned[1:-1]
        try:
            f = float(cleaned)
            return -f if is_paren else f
        except ValueError: return default
    return default


def _note_val(stmt, key):
    n = (stmt.get("notes") or {}).get(key) or {}
    return _safe_num(n.get("value"))


def build_sovereign_state(gfti_stmt: dict, 
                          country: str = "Barbados",
                          entity_type: str = "Central Government",
                          nominal_gdp: float = 16_193_000_000,
                          fdi_inflows: float = 476_900_000,
                          current_account_deficit: float = 532_600_000,
                          gross_reserves: float = 2_827_500_000,
                          weeks_import_cover: float = 22.8) -> dict:
    """
    Entity-aware translation from GFTI extraction to sovereign_state.json.
    """
    notes = gfti_stmt.get("notes") or {}
    bs = gfti_stmt.get("bs") or {}
    is_ = gfti_stmt.get("is_") or {}
    audit = gfti_stmt.get("audit") or {}
    metadata = gfti_stmt.get("metadata") or {}

    provenance = {}

    # ─── PILLAR 1: OFFICIAL DEBT ───
    # Only trust the uploaded PDF for official debt if it's a Central Government statement.
    if entity_type == "Central Government":
        official_debt = _note_val(gfti_stmt, "total_public_debt")
        if official_debt == 0:
            official_debt = _safe_num(bs.get("total_liabilities"))
        if official_debt > 0:
            provenance["official_debt"] = f"extracted · {metadata.get('reporting_period', 'N/A')}"
        else:
            official_debt = 15_318_200_000.0
            provenance["official_debt"] = "fallback · MoF 2026 Mid-Year Review"
    else:
        # CB / SOE uploads: use the MoF figure as the baseline sovereign debt
        official_debt = 15_318_200_000.0
        provenance["official_debt"] = "fallback · MoF 2026 Mid-Year Review (entity's own debt excluded)"

    # ─── PILLAR 2: HIDDEN LIABILITIES ───

    # 2a. Central Bank Negative Equity
    cbb_neg_eq = 0.0
    net_assets = _safe_num(bs.get("net_assets"))
    if net_assets < 0:
        cbb_neg_eq = abs(net_assets)
        provenance["cbb_neg_eq"] = f"extracted from bs.net_assets (${net_assets:,.0f})"
    else:
        cbb_neg_eq = 1_422_167_000.0
        provenance["cbb_neg_eq"] = "fallback · CBB 2025 Annual Report, Note 1 (Page 70)"

    # 2b. NIS Actuarial Shortfall
    nis_shortfall = _note_val(gfti_stmt, "nis_unfunded_actuarial_shortfall")
    if nis_shortfall == 0:
        nis_shortfall = 4_200_000_000.0
        provenance["nis_shortfall"] = "fallback · NIS 17th Actuarial Review (2020), Table 1.6 (Page 16)"
    else:
        provenance["nis_shortfall"] = "extracted"

    # 2c. Government Pension Liability
    govt_pension = _note_val(gfti_stmt, "govt_pension_unfunded_liability")
    if govt_pension == 0:
        pension_recorded = (notes.get("pension_recorded") or {}).get("value")
        payroll = _safe_num(is_.get("payroll") or is_.get("personal_emoluments"))
        if payroll == 0:
            payroll = 863_924_381.0  # AG Report 2023, Note 4
        if pension_recorded is False:
            govt_pension = payroll * 2.5
            provenance["govt_pension"] = f"2.5× payroll proxy (${payroll:,.0f}) · AG Note 8"
        else:
            govt_pension = 2_159_811_000.0
            provenance["govt_pension"] = "fallback · AG Report 2023, Note 8 (Page 23)"

    # 2d. SOE Arrears
    soe_arrears = _note_val(gfti_stmt, "soe_arrears")
    if soe_arrears == 0:
        soe_arrears = 74_600_000.0
        provenance["soe_arrears"] = "fallback · MoF Mid-Year Review 2025 (Page 22)"
    else:
        provenance["soe_arrears"] = "extracted"

    # 2e. Guarantees & Deferred Payments
    guarantees = _note_val(gfti_stmt, "parliament_guarantees_and_deferred_payments")
    if guarantees == 0:
        guarantees = 338_600_000.0
        provenance["guarantees"] = "fallback · SINOPHARM (313.6M) + QEH RBC (25M)"
    else:
        provenance["guarantees"] = "extracted"

    # ─── PILLAR 3: EXTERNAL SECTOR ───
    ext = {
        "gross_reserves": gross_reserves,
        "weeks_of_import_cover": weeks_import_cover,
        "current_account_deficit_annual": current_account_deficit,
        "fdi_inflows_annual": fdi_inflows,
        "external_debt_service_ratio": 0.256,
    }

    state = {
        "country": country,
        "last_updated": "auto-populated",
        "currency_peg": "BDS$2.00 = US$1.00",
        "nominal_gdp": nominal_gdp,
        "official_debt": {
            "central_govt": round(official_debt, 0),
            "source": provenance["official_debt"],
        },
        "hidden_liabilities": {
            "cbb_negative_equity": round(cbb_neg_eq, 0),
            "nis_unfunded_actuarial_shortfall": round(nis_shortfall, 0),
            "govt_pension_unfunded_liability": round(govt_pension, 0),
            "soe_arrears": round(soe_arrears, 0),
            "parliament_guarantees_and_deferred_payments": round(guarantees, 0),
        },
        "external_sector": ext,
        "_provenance": {
            "entity_type": entity_type,
            "audit_opinion": audit.get("opinion_type", "unknown"),
            "reporting_period": metadata.get("reporting_period", "N/A"),
            **provenance,
        }
    }
    return state


def write_sovereign_state(gfti_stmt: dict, output_path: str = "data/sovereign_state.json", entity_type: str = "Central Government", **kwargs) -> str:
    state = build_sovereign_state(gfti_stmt, entity_type=entity_type, **kwargs)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(state, f, indent=2)
    return str(out)