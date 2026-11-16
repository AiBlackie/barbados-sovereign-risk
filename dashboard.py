# dashboard.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import os
from navigator.true_debt import TrueDebtCalculator
from navigator.peg_defense import PegDefenseMonitor

from report_generator import generate_sovereign_report

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Sovereign Risk Navigator", 
    page_icon="🌍", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .metric-label { font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 36px; font-weight: 800; margin-top: -5px; }
    .metric-delta { font-size: 14px; font-weight: 600; }
    .alert-box { padding: 20px; border-radius: 5px; background-color: #fff3e0; border-left: 5px solid #e65100; color: #e65100; font-weight: bold; margin-bottom: 20px; font-size: 18px; }
    .success-box { padding: 20px; border-radius: 5px; background-color: #e8f5e9; border-left: 5px solid #2e7d32; color: #2e7d32; font-weight: bold; margin-bottom: 20px; font-size: 18px; }
    .pillar-text { font-size: 18px; line-height: 1.6; margin-bottom: 20px; }
    .evidence-box { background-color: #1e1e1e; padding: 15px; border-radius: 5px; border-left: 4px solid #1f77b4; margin-top: 10px; margin-bottom: 10px;}
    .evidence-quote { font-style: italic; color: #ddd; font-size: 15px; margin-bottom: 10px; }
    .evidence-source { font-weight: bold; color: #aaa; font-size: 13px; }
    .footnote { font-size: 11px; color: #999; margin-top: -8px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- LOAD DATA ---
STATE_FILE = "data/sovereign_state.json"
if not os.path.exists(STATE_FILE):
    st.error(f"State file not found at {STATE_FILE}. Please create it.")
    st.stop()

debt_calc = TrueDebtCalculator(state_file=STATE_FILE)
peg_calc = PegDefenseMonitor(state_file=STATE_FILE)

debt_data = debt_calc.calculate()
peg_data = peg_calc.analyze()

with open(STATE_FILE, "r") as f:
    raw_state = json.load(f)
    ext = raw_state["external_sector"]

# HARDCODED EVIDENCE
FORENSIC_EVIDENCE = debt_data["forensic_evidence"]

# --- SIDEBAR: SHOCK SIMULATOR ---
with st.sidebar:
    st.header("⚠️ External Sector Stress Test")
    st.write("Model the impact of a global recession on reserve adequacy.")
    
    fdi_shock = st.slider("Drop in FDI Inflows (%)", min_value=0, max_value=100, value=100)
    include_debt_service = st.checkbox("Include External Debt Service", value=True, help="Adds principal repayments (IMF, Eurobonds) to the burn rate.")
    
    current_fdi = ext["fdi_inflows_annual"]
    shocked_fdi = current_fdi * (1 - (fdi_shock / 100))
    
    cad = ext["current_account_deficit_annual"]
    estimated_debt_amortization = cad * 0.25 if include_debt_service else 0 
    new_burn_rate = cad + estimated_debt_amortization - shocked_fdi

    st.divider()
    
    if new_burn_rate > 0:
        weekly_imports = ext["gross_reserves"] / ext["weeks_of_import_cover"]
        target_reserves = weekly_imports * 12
        
        if ext["gross_reserves"] <= target_reserves:
            months_to_danger = 0
        else:
            months_to_danger = ((ext["gross_reserves"] - target_reserves) / new_burn_rate) * 12
            
        st.error(f"**NET BURN RATE:** BDS ${new_burn_rate:,.0f}/year")
        st.error(f"**TIME TO 12-WEEK BENCHMARK:** {months_to_danger:.1f} Months")
    else:
        st.success("Reserves are stable under these conditions.")

# --- MAIN PAGE ---
st.title("🌍 Sovereign Risk Navigator: Barbados")
st.markdown("*A forensic consolidation of public sector liabilities and external buffer adequacy.*")

# --- DOWNLOAD BUTTON ---
col_title, col_btn = st.columns([4, 1])
with col_btn:
    report_html = generate_sovereign_report(STATE_FILE)
    st.download_button(
        label="📄 Download Full Brief (HTML)",
        data=report_html,
        file_name="Barbados_Sovereign_Risk_Brief.html",
        mime="text/html",
        type="primary"
    )

st.divider()

# --- TOP LEVEL METRICS ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f'<div class="metric-label">Official Central Govt Debt-to-GDP</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{debt_data["official_ratio_pct"]}%</div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-delta">Reported Figure</div>', unsafe_allow_html=True)
    st.markdown('<div class="footnote">Reported at 96.0% under IMF FY-GDP basis; shown here at 94.6% under CY-GDP for comparability with CBB data.</div>', unsafe_allow_html=True)

with col2:
    st.markdown(f'<div class="metric-label">Consolidated Public Sector Debt-to-GDP</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value" style="color: #b00020;">{debt_data["true_ratio_pct"]}%</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-delta">IPSAS-Basis (+{debt_data["true_ratio_pct"] - debt_data["official_ratio_pct"]:.1f}% Gap)</div>', unsafe_allow_html=True)

with col3:
    st.markdown(f'<div class="metric-label">Peg Vulnerability Score</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{peg_data["peg_vulnerability_score"]}/100</div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-delta">Currency Risk</div>', unsafe_allow_html=True)

st.divider()

# --- PILLAR 1: TRUE DEBT ---
st.subheader("1. Consolidated Liability Composition")

html_text = f"""
<div class="pillar-text">
The Central Government reports a debt stock of <b>BDS ${debt_data['official_debt_bds']:,.0f}</b>. 
When contingent liabilities and public sector obligations are consolidated under IPSAS 35 — including the BDS $1.48B in Parliamentary Resolution borrowing (2022-2025) — the total public sector liability reaches <b>BDS ${debt_data['true_debt_bds']:,.0f}</b>.
</div>
"""
st.markdown(html_text, unsafe_allow_html=True)

breakdown = debt_data["hidden_gap_breakdown"]

# --- SHARED DATA ---
liability_labels = [
    "Central Government Debt", 
    "Central Bank Negative Equity", 
    "NIS Actuarial Shortfall", 
    "Government Pension Liability",
    "SOE Arrears", 
    "SOE Non-Guaranteed Debt",
    "Parliamentary Resolutions (2022-2025)"
]
liability_values = [
    debt_data['official_debt_bds'], 
    breakdown['cbb_negative_equity'], 
    breakdown['nis_unfunded_actuarial_shortfall'], 
    breakdown['govt_pension_unfunded_liability'],
    breakdown['soe_arrears'], 
    breakdown.get('soe_non_guaranteed_debt', 0),
    debt_data.get('total_parl_resolutions', 0)
]
time_horizons = [
    "Contracted", 
    "Immediate (recap.)", 
    "Long-term (2036 depletion)", 
    "Continuous draw",
    "Immediate", 
    "Immediate (stock)",
    "Conditional (multi-year)"
]
colors = {
    "Central Government Debt": "#1f77b4",
    "Central Bank Negative Equity": "#d62728",
    "NIS Actuarial Shortfall": "#ff7f0e",
    "Government Pension Liability": "#2ca02c",
    "SOE Arrears": "#9467bd",
    "SOE Non-Guaranteed Debt": "#e377c2",
    "Parliamentary Resolutions (2022-2025)": "#17becf"
}

# ============================================================
# CHART A: RECONCILIATION BRIDGE
# ============================================================
st.markdown("#### A. Reconciliation Bridge: Official to Consolidated")

official_val = debt_data['official_debt_bds']
hidden_additions = liability_values[1:]
hidden_labels = liability_labels[1:]

# Build a horizontal bar chart to simulate the bridge
bridge_y = ["Consolidated\nTotal"] + hidden_labels[::-1] + ["Official\nBase"]
bridge_x = [debt_data['true_debt_bds']] + hidden_additions[::-1] + [official_val]
bridge_colors = ["#b00020"] + [colors[l] for l in hidden_labels[::-1]] + ["#1f77b4"]
bridge_text = [f"${debt_data['true_debt_bds']/1e9:.2f}B"] + [f"+${v/1e9:.2f}B" for v in hidden_additions[::-1]] + [f"${official_val/1e9:.2f}B"]

fig_bridge = go.Figure(go.Bar(
    x=bridge_x,
    y=bridge_y,
    orientation="h",
    marker=dict(color=bridge_colors),
    text=bridge_text,
    textposition="outside",
    textfont=dict(size=12, color="#888"),
    hovertemplate="<b>%{y}</b><br>BDS $%{x:,.0f}<extra></extra>"
))

fig_bridge.update_layout(
    title=dict(text="", font=dict(size=15)),
    showlegend=False,
    height=520,
    margin=dict(t=20, b=40, l=200, r=40),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif"),
    xaxis=dict(
        title="BDS (Billions)",
        tickformat=",.0f",
        tickprefix="BDS $",
        gridcolor="rgba(128, 128, 128, 0.2)",
        range=[0, debt_data['true_debt_bds'] * 1.15]
    ),
    yaxis=dict(tickfont=dict(size=11))
)

st.plotly_chart(fig_bridge, use_container_width=True)

# ============================================================
# CHART B: GROUPED HORIZONTAL BARS
# ============================================================
st.markdown("#### B. Official vs. Consolidated: The Gap Visualized")

y_labels = ["Consolidated<br>(IPSAS 35)", "Official<br>(Reported)"]
fig_stacked = go.Figure()

# Bar 1: Official Total (Base)
fig_stacked.add_trace(go.Bar(
    name="Central Government Debt",
    y=[y_labels[1], y_labels[0]], 
    x=[debt_data['official_debt_bds'], debt_data['official_debt_bds']],
    orientation="h",
    marker=dict(color=colors["Central Government Debt"]),
    text=[f"BDS ${debt_data['official_debt_bds']/1e9:.2f}B", ""],
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(color="white", size=13, family="Inter"),
    hovertemplate="<b>Central Government Debt</b><br>BDS $%{x:,.0f}<extra></extra>",
    showlegend=True
))

# Bars 2-N: Hidden Segments (Only on Consolidated row)
for i, label in enumerate(hidden_labels):
    val = hidden_additions[i]
    horizon = time_horizons[i + 1]
    fig_stacked.add_trace(go.Bar(
        name=label,
        y=[None, y_labels[0]], 
        x=[0, val], 
        orientation="h",
        marker=dict(color=colors[label]),
        text=["", f"{horizon}"],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="white", size=9, family="Inter"),
        hovertemplate=f"<b>{label}</b><br>BDS $%{{x:,.0f}}<br>Horizon: {horizon}<extra></extra>",
        showlegend=True
    ))

gap = debt_data['hidden_gap_bds']
fig_stacked.add_annotation(
    x=debt_data['true_debt_bds'],
    y=y_labels[0],
    text=f"<b>GAP: BDS ${gap/1e9:.2f}B</b><br>(+{debt_data['true_ratio_pct'] - debt_data['official_ratio_pct']:.1f} pp of GDP)",
    showarrow=True,
    arrowhead=2,
    arrowcolor="#b00020",
    ax=60,
    ay=0,
    font=dict(color="#b00020", size=13),
    bgcolor="white",
    bordercolor="#b00020",
    borderwidth=1.5,
    borderpad=6
)

fig_stacked.update_layout(
    title=dict(text="", font=dict(size=15)),
    barmode="stack",
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5,
        font=dict(size=10),
        title=None
    ),
    height=380,
    margin=dict(t=80, b=30, l=100, r=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif"),
    xaxis=dict(
        title="BDS (Billions)",
        tickformat=",.0f",
        tickprefix="BDS $",
        gridcolor="rgba(128, 128, 128, 0.2)",
        range=[0, debt_data['true_debt_bds'] * 1.20]
    ),
    yaxis=dict(tickfont=dict(size=12))
)

st.plotly_chart(fig_stacked, use_container_width=True)

st.caption("**How to read these charts:** Chart A shows the audit-grade reconciliation — starting from the official figure and adding each excluded liability. Chart B compares the two totals side-by-side. Labels indicate the *time horizon* and *certainty* of each liability, since they are not interchangeable obligations.")

# --- FORENSIC EVIDENCE SECTION ---
st.markdown("### 🔍 Forensic Evidence & Official Citations")
st.write("This dashboard is built on deterministic extraction from official government and IMF documents. The unconsolidated liabilities are legal obligations admitted by the state.")

with st.expander("0. The IMF's Own Disclosure (The Smoking Gun)"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['imf_disclosure']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['imf_disclosure']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The IMF's 2026 Article IV Report explicitly confirms in its own Debt Coverage and Disclosure table that both the NIS (Social security funds) and the Central Bank are **not consolidated** in its formal Debt Sustainability Analysis. This is the IMF's own admission that the two largest liabilities in this brief sit outside the official debt perimeter.")

with st.expander("1. Central Bank Insolvency (The 2018 Restructuring)"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['cbb_negative_equity']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['cbb_negative_equity']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The 2018 debt restructuring transferred BDS $1.42 Billion of sovereign debt onto the balance sheet of the Central Bank. The IMF acknowledges a recapitalization plan exists, but it relies on profit retention. At current profit levels, filling this hole would take decades. The negative equity remains an implicit sovereign obligation.")

with st.expander("2. NIS Actuarial Depletion Risk"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['nis_shortfall']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['nis_shortfall']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The 2022-2023 NIS reforms improved the scheme's sustainability, and the IMF is correct that the fund will not be exhausted by 2036. However, the IMF's own Figure 6 (Page 60) shows a **persistent pension financing need of 0.2-0.4 pp of GDP per year for the next 50 years**. The BDS $4.2B shortfall represents a floor, not a full accounting. The scheme will require continuous government support in perpetuity, and it remains excluded from the IMF's formal DSA. **Importantly, the IMF evaluates the NIS (Social Security) but does not evaluate the Government Pension Plan for public servants, which is a separate, unfunded obligation.**")

with st.expander("3. Unfunded Government Pension Liability"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['govt_pension_liability']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['govt_pension_liability']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The government operates a pay-as-you-go pension system for public servants. Unlike the NIS (which covers private-sector workers and holds ~$4.2B in assets), the Government Pension Plan has no ring-fenced assets. The Auditor General explicitly flagged this omission as a basis for the adverse opinion. Using a conservative 2.5× payroll multiplier, the present value of accrued pension obligations is estimated at **BDS $2.16 Billion** — a conservative floor.")

with st.expander("4. SOE Debt (Stock vs. Arrears)"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['soe_debt']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['soe_debt']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** This brief reconciles two distinct SOE exposures: (1) the BDS $426 million in non-guaranteed SOE debt (2.7% of GDP) disclosed in the IMF 2026 report, and (2) the BDS $74.6 million in arrears from the MoF Mid-Year Review, which represents unpaid bills at the NPC, BWA and SSA. Both are excluded from the headline sovereign debt figure, and both are implicit fiscal risks. The IMF explicitly states that 'implicit government guarantees remain a concern'.")

with st.expander("5. The IMF's DSA Perimeter (What It Includes vs. What It Excludes)"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['imf_dsa_boundary']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['imf_dsa_boundary']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['imf_contingent_liabilities']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['imf_contingent_liabilities']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The IMF's DSA does include BDS $147.2M in public guarantees and 1.3% of GDP in expenditure arrears. But it explicitly excludes the BDS $426M in non-guaranteed SOE debt (2.6% of GDP). This brief captures the excluded amount as an additional line item. The IMF's own footnote is the strongest possible evidence that the official DSA perimeter is incomplete.")

with st.expander("6. The IMF's SRDSF Assessment vs. the Consolidated Reality"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['imf_srdsf_assessment']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['imf_srdsf_assessment']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The IMF's SRDSF assesses Barbados' debt as sustainable. But this assessment relies on a perimeter that excludes the BDS $11.56B gap identified in this brief. If those liabilities were consolidated, the SRDSF's mechanical signal would likely shift from 'moderate' to 'high' risk of sovereign stress. This is not a critique of the IMF's methodology — it is an observation about the boundary of the data it uses.")

with st.expander("7. The 2025 Eurobond (Parliamentary Resolution, June 24, 2025)"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['parliamentary_resolution_2025']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['parliamentary_resolution_2025']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The June 2025 liability management operation restructured the Government's near-term maturity profile. The 6.5% 2029 Eurobond was subject to a sinking-fund amortization schedule with principal repayments commencing in April 2025. The new US$500M bond carries an 8.0% coupon and includes a five-year principal grace period until December 2030. The LMO eliminates near-term amortization pressure and extends the maturity profile by six years, in exchange for a higher annual coupon. Proceeds were allocated to refinancing the 2029 bond and prepaying IMF EFF obligations — not to addressing the CBB negative equity or the NIS actuarial shortfall. The 2035 maturity date coincides with the BERT 2026 target of reaching 60% debt-to-GDP by FY2035/36.")

with st.expander("8. Parliamentary Resolutions (2022-2025): The Full Borrowing Record"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['parliamentary_resolutions']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['parliamentary_resolutions']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The Government of Barbados has borrowed approximately **BBD $1.48 billion and USD $37.4 million** through nine Parliamentary Resolutions between 2022 and 2025. These borrowings are legally binding, approved by Parliament, and classified as 'Special Loans' rather than 'Central Government Debt.' They are excluded from the IMF's DSA perimeter and from the headline 96% debt-to-GDP figure. The nine resolutions are: SINOPHARM (BBD $313.6M), CARICOM CDF (USD $12.4M), Exim Bank of China (BBD $256.6M), Saudi Fund Urban Renewal (BBD $68.4M), Saudi Fund Polyclinic (BBD $117M), CIBC/Scotiabank/RBC Syndicated Facility (BBD $600M), Kensington Oval (USD $25M), UWI/CDB (BBD $2M), and OPEC Fund (BBD $100M).")

with st.expander("9. The Excluded 2013 QEH/RBC Loan (Data Audit)"):
    st.markdown(f"""
    <div class="evidence-box">
        <div class="evidence-quote">"{FORENSIC_EVIDENCE['qeh_rbc_loan_excluded']['quote']}"</div>
        <div class="evidence-source">Source: {FORENSIC_EVIDENCE['qeh_rbc_loan_excluded']['source']}</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("**Analytical Implication:** The QEH RBC loan (BDS $25M) from the December 5, 2013 Parliamentary Resolution is excluded from the liability register. The loan carried a 7-year term from disbursement, implying maturity around 2020-2021. There is no evidence of extension or refinancing in the 2025-2026 documentation (MoF Mid-Year Review, IMF Article IV, CBB Annual Report). It is noted here for completeness but is not counted as an outstanding liability. This demonstrates forensic rigor: each line item is audited against current documentation.")

st.divider()

# --- PILLAR 2: PEG DEFENSE ---
st.subheader("2. External Buffer Adequacy")
st.markdown(f'<div class="pillar-text">Gross Reserves: <b>BDS ${ext["gross_reserves"]:,.0f}</b>. Import Cover: <b>{ext["weeks_of_import_cover"]} weeks</b>.</div>', unsafe_allow_html=True)
st.markdown(f'<div class="pillar-text">CBB Insolvency Ratio (Negative Equity vs Reserves): <b>{peg_data["insolvency_ratio_pct"]}%</b></div>', unsafe_allow_html=True)
st.markdown(f'<div class="pillar-text">IMF 2026 Assessment: Reserves are <b>{ext.get("imf_reserve_months", 6.0)} months of imports ({ext.get("imf_ara_percent", 194)}% of ARA)</b> — assessed as "ample" to support the peg.</div>', unsafe_allow_html=True)

st.divider()

# --- PILLAR 3: HIDDEN LIABILITY REGISTER ---
st.subheader("3. Unconsolidated Liability Register")

total_hidden_liabilities = debt_data['true_debt_bds'] - debt_data['official_debt_bds']

st.metric(
    label="TOTAL UNCONSOLIDATED LIABILITIES (Excluded from Headline Debt)", 
    value=f"BDS ${total_hidden_liabilities:,.0f}",
    delta="IPSAS 35 Consolidation Gap",
    delta_color="inverse"
)

register_data = pd.DataFrame([
    {"Entity / Project": "QEH (China SINOPHARM)", "Amount (BDS)": 313600000, "Type": "Deferred Payment Agreement", "Source": "Parliament Resolution 2025"},
    {"Entity / Project": "CARICOM Development Fund", "Amount (BDS)": 24800000, "Type": "Term Loan (Wastewater)", "Source": "Parliament Resolution 2024"},
    {"Entity / Project": "Exim Bank of China", "Amount (BDS)": 256600000, "Type": "Term Loan (Roads)", "Source": "Parliament Resolution 2022"},
    {"Entity / Project": "Saudi Fund (Urban Renewal)", "Amount (BDS)": 68400000, "Type": "Term Loan (Infrastructure)", "Source": "Parliament Resolution 2025"},
    {"Entity / Project": "Saudi Fund (Polyclinic)", "Amount (BDS)": 117000000, "Type": "Term Loan (Health)", "Source": "Parliament Resolution 2025"},
    {"Entity / Project": "CIBC/Scotiabank/RBC", "Amount (BDS)": 600000000, "Type": "Sustainability-Linked Loan", "Source": "Parliament Resolution 2024"},
    {"Entity / Project": "Kensington Oval", "Amount (BDS)": 50000000, "Type": "Government Guarantee (SOE)", "Source": "Parliament Resolution 2023"},
    {"Entity / Project": "UWI (CDB)", "Amount (BDS)": 2000000, "Type": "Government Guarantee (UWI)", "Source": "Parliament Resolution 2022"},
    {"Entity / Project": "OPEC Fund", "Amount (BDS)": 100000000, "Type": "Term Loan (Social Services)", "Source": "Parliament Resolution 2025"},
    {"Entity / Project": "SOE Arrears (BWA, NPC, SSA)", "Amount (BDS)": 74600000, "Type": "Unconsolidated SOE Arrears", "Source": "MoF Mid-Year Review 2025 (Page 22)"},
    {"Entity / Project": "SOE Non-Guaranteed Debt", "Amount (BDS)": 426000000, "Type": "Non-Guaranteed SOE Debt Stock", "Source": "IMF 2026 Article IV (Page 87)"},
    {"Entity / Project": "Central Bank of Barbados", "Amount (BDS)": 1422167000, "Type": "Negative Equity (Insolvency)", "Source": "CBB 2024/2025 Annual Report"},
    {"Entity / Project": "NIS Pension Fund", "Amount (BDS)": 4200000000, "Type": "Actuarial Depletion Risk (2036)", "Source": "17th Actuarial Review 2020"},
    {"Entity / Project": "Government Public Pension Plan", "Amount (BDS)": 2159811000, "Type": "Unfunded Defined Benefit (Estimate)", "Source": "AG Report 2023, Note 8 (Page 23)"},
])

st.dataframe(
    register_data.style.format({"Amount (BDS)": "{:,.0f}"}),
    use_container_width=True,
    hide_index=True
)

st.caption("Data compiled from official Government of Barbados, CBB, IMF 2026 Article IV, and Parliamentary Resolution documents. The 2013 QEH/RBC loan (BDS $25M) is excluded as matured. Government Pension Liability is a conservative estimate (2.5× annual payroll) pending the official actuarial valuation.")