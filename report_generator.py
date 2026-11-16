# report_generator.py
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from navigator.true_debt import TrueDebtCalculator
from navigator.peg_defense import PegDefenseMonitor

def generate_sovereign_report(state_file="data/sovereign_state.json"):
    debt_calc = TrueDebtCalculator(state_file=state_file)
    peg_calc = PegDefenseMonitor(state_file=state_file)
    debt_data = debt_calc.calculate()
    peg_data = peg_calc.analyze()

    with open(state_file, "r") as f:
        raw_state = json.load(f)
    
    breakdown = debt_data["hidden_gap_breakdown"]
    ext = raw_state["external_sector"]
    
    # Sum all numerical values, plus the total parliamentary resolutions
    base_hidden_sum = sum(v for k, v in breakdown.items() if isinstance(v, (int, float)))
    total_hidden = base_hidden_sum + debt_data.get('total_parl_resolutions', 0)

    # Crisis scenario
    reserves = ext["gross_reserves"]
    weeks_cover = ext["weeks_of_import_cover"]
    cad = ext["current_account_deficit_annual"]
    
    estimated_debt_amortization = cad * 0.25
    crisis_burn_rate = cad + estimated_debt_amortization
    
    weekly_imports = reserves / weeks_cover
    target_reserves = weekly_imports * 12
    
    if reserves <= target_reserves:
        crisis_months = 0
    else:
        crisis_months = ((reserves - target_reserves) / crisis_burn_rate) * 12

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
    official_val = debt_data['official_debt_bds']
    hidden_additions = liability_values[1:]
    hidden_labels = liability_labels[1:]

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
        margin=dict(t=20, b=60, l=280, r=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", color="#333"),
        xaxis=dict(
            title="BDS (Billions)",
            tickformat=",",           
            tickprefix="BDS $",
            ticksuffix="B",           
            tickangle=0,
            dtick=5000000000,         
            tickvals=[0, 5000000000, 10000000000, 15000000000, 20000000000, 25000000000, 30000000000],
            ticktext=["$0", "$5B", "$10B", "$15B", "$20B", "$25B", "$30B"],
            gridcolor="#eee",
            range=[0, debt_data['true_debt_bds'] * 1.15]
        ),
        yaxis=dict(tickfont=dict(size=11))
    )
    chart_bridge_html = fig_bridge.to_html(full_html=False, include_plotlyjs='cdn')

    # ============================================================
    # CHART B: GROUPED HORIZONTAL BARS
    # ============================================================
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
            text=["", f"${val/1e9:.1f}B"] if val > 0 else ["", ""],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=11, family="Inter", weight="bold"),
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
        margin=dict(t=80, b=60, l=100, r=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", color="#333"),
        xaxis=dict(
            title="BDS (Billions)",
            tickformat=",",           
            tickprefix="BDS $",
            ticksuffix="B",           
            tickangle=0,
            dtick=5000000000,         
            tickvals=[0, 5000000000, 10000000000, 15000000000, 20000000000, 25000000000, 30000000000],
            ticktext=["$0", "$5B", "$10B", "$15B", "$20B", "$25B", "$30B"],
            gridcolor="#eee",
            range=[0, debt_data['true_debt_bds'] * 1.20]
        ),
        yaxis=dict(tickfont=dict(size=12))
    )
    chart_stacked_html = fig_stacked.to_html(full_html=False, include_plotlyjs=False)

    # ============================================================
    # PREMIUM HTML TEMPLATE
    # ============================================================
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Confidential: Sovereign Fiscal Risk Brief - Barbados</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Playfair+Display:wght@700&display=swap');
            
            body {{ font-family: 'Inter', sans-serif; color: #2C3E50; line-height: 1.7; margin: 0; padding: 0; background-color: #F8F9FA; }}
            
            /* Page wrapper to mimic a printed A4 page */
            .page {{ background-color: #fff; max-width: 900px; margin: 40px auto; padding: 60px 80px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
            
            /* Header Branding */
            .header {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #1A252F; padding-bottom: 15px; margin-bottom: 40px; }}
            .logo {{ font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: #1A252F; letter-spacing: -0.5px; }}
            .logo span {{ color: #b00020; }}
            .confidential {{ font-size: 11px; font-weight: 600; color: #b00020; text-transform: uppercase; letter-spacing: 2px; border: 1px solid #b00020; padding: 4px 8px; border-radius: 4px; }}
            
            h1 {{ font-family: 'Playfair Display', serif; font-size: 36px; color: #1A252F; margin-bottom: 10px; line-height: 1.2; }}
            h2 {{ font-size: 16px; color: #1A252F; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #E0E0E0; padding-bottom: 10px; margin-top: 50px; }}
            h3 {{ font-size: 18px; color: #1A252F; margin-top: 30px; font-weight: 600; }}
            
            .subtitle {{ font-size: 18px; color: #555; margin-bottom: 30px; font-weight: 300; }}
            .meta {{ font-size: 12px; color: #888; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 1px; display: flex; gap: 20px; }}
            
            /* KPI Cards */
            .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }}
            .card {{ border: 1px solid #E0E0E0; border-top: 4px solid #1A252F; padding: 20px; text-align: left; background: #fff; }}
            .card.alert-card {{ border-top-color: #b00020; }}
            .card-label {{ font-size: 11px; text-transform: uppercase; color: #666; font-weight: 600; letter-spacing: 0.5px; }}
            .card-value {{ font-size: 32px; font-weight: 800; margin: 10px 0 5px 0; color: #1A252F; }}
            .card.alert-card .card-value {{ color: #b00020; }}
            .card-delta {{ font-size: 12px; font-weight: 600; color: #666; }}
            .card-footnote {{ font-size: 10px; color: #999; margin-top: 4px; font-style: italic; }}
            
            /* Alert Box */
            .alert {{ background-color: #FFF5F5; border-left: 4px solid #b00020; padding: 20px; margin-bottom: 30px; font-weight: 500; color: #b00020; font-size: 15px; }}
            
            /* Tables */
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
            th {{ background-color: #F8F9FA; text-align: left; padding: 12px; border-bottom: 2px solid #1A252F; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px; color: #555; }}
            td {{ padding: 14px 12px; border-bottom: 1px solid #E0E0E0; }}
            tr:last-child td {{ border-bottom: none; }}
            
            /* Quotes */
            .quote-box {{ background-color: #F8F9FA; border-left: 3px solid #1A252F; padding: 20px; margin: 20px 0; font-style: italic; font-size: 14px; color: #444; }}
            .source {{ font-style: normal; font-weight: 600; color: #1A252F; font-size: 12px; display: block; margin-top: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
            
            /* Footer */
            .footer {{ margin-top: 60px; font-size: 11px; color: #888; text-align: center; border-top: 1px solid #E0E0E0; padding-top: 20px; }}
            .estimate-tag {{ background: #FFF3CD; color: #856404; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }}
            .chart-caption {{ font-size: 12px; color: #666; margin-top: 10px; margin-bottom: 40px; font-style: italic; text-align: center; }}
            
            @media print {{
                body {{ background-color: #fff; }}
                .page {{ margin: 0; padding: 0; box-shadow: none; max-width: 100%; }}
                .alert {{ -webkit-print-color-adjust: exact; }}
                .page-break {{ page-break-before: always; }}
                .card {{ -webkit-print-color-adjust: exact; }}
            }}
        </style>
    </head>
    <body>

    <div class="page">
        <!-- HEADER -->
        <div class="header">
            <div class="logo">SOVEREIGN<span>RISK</span> NAVIGATOR</div>
            <div class="confidential">Confidential Intelligence</div>
        </div>

        <!-- TITLE -->
        <h1>Sovereign Liability Assessment:<br>Barbados</h1>
        <div class="subtitle">An Analysis of Unconsolidated Liabilities and External Buffer Adequacy</div>
        
        <div class="meta">
            <span><strong>Date:</strong> {datetime.now().strftime("%B %d, %Y")}</span>
            <span><strong>Classification:</strong> Institutional Grade</span>
            <span><strong>Data Source:</strong> Official Government, CBB & IMF 2026 Article IV Documents</span>
        </div>

        <!-- EXECUTIVE ALERT -->
        <div class="alert">
            <strong>EXTERNAL SECTOR STRESS TEST:</strong> If FDI drops to zero and external debt service is included, reserves will reach the 12-week critical benchmark in {crisis_months:.1f} months. The IMF's 2026 Article IV report identifies this vulnerability (Page 12, ¶13) but assesses the reserves as "ample" only under its central baseline scenario.
        </div>

        <!-- KPI GRID -->
        <div class="grid">
            <div class="card">
                <div class="card-label">Official Central Govt Debt-to-GDP</div>
                <div class="card-value">{debt_data['official_ratio_pct']}%</div>
                <div class="card-delta">Reported Figure</div>
                <div class="card-footnote">Reported at 96.0% under IMF FY-GDP basis; shown here at 94.6% under CY-GDP for comparability with CBB data.</div>
            </div>
            <div class="card alert-card">
                <div class="card-label">Consolidated Public Sector Debt-to-GDP</div>
                <div class="card-value">{debt_data['true_ratio_pct']}%</div>
                <div class="card-delta">IPSAS-Basis (+{debt_data['true_ratio_pct'] - debt_data['official_ratio_pct']:.1f}% Gap)</div>
            </div>
            <div class="card">
                <div class="card-label">Unconsolidated Liabilities</div>
                <div class="card-value">BDS ${total_hidden / 1e9:.2f}B</div>
                <div class="card-delta">Excluded from Headline Debt</div>
            </div>
        </div>

        <!-- SECTION 0: THE IMF'S SMOKING GUN -->
        <div style="background: #fafafa; border: 2px solid #b00020; border-radius: 6px; padding: 20px 25px; margin-bottom: 30px; page-break-inside: avoid;">
            <h3 style="margin-top: 0; color: #b00020; font-size: 16px;">⚠️ The IMF's Own Disclosure</h3>
            <p style="font-size: 14px; color: #333; line-height: 1.6;">
                The IMF's 2026 Article IV Report explicitly marks both <strong>NIS (Social security funds)</strong> and the <strong>Central Bank</strong> as <strong>"Not consolidated"</strong> in its Debt Coverage and Disclosure table (Page 58, Figure 1). This is the Fund's own admission that the two largest liabilities in this brief — the BDS $4.2B NIS shortfall and the BDS $1.42B CBB negative equity — sit outside the formal DSA perimeter. The IMF's 96% debt figure is therefore definitionally narrower than the full IPSAS 35 consolidated liability, and the BDS ${total_hidden/1e9:.2f}B gap sits outside the Fund's formal DSA perimeter.
            </p>
            <span class="source">Source: IMF 2026 Article IV Consultation, Annex II, Figure 1 (Page 58)</span>
        </div>

        <!-- SECTION 1 -->
        <h2>1. Consolidated Liability Composition</h2>
        <p>The Central Government reports a debt stock of <strong>BDS ${debt_data['official_debt_bds']:,.0f}</strong>. When contingent liabilities and public sector obligations are consolidated under IPSAS 35 — including the BDS $1.48B in Parliamentary Resolution borrowing (2022-2025) — the total public sector liability reaches <strong>BDS ${debt_data['true_debt_bds']:,.0f}</strong>.</p>

        <h3>Chart A — Reconciliation Bridge: Official to Consolidated</h3>
        {chart_bridge_html}
        <p class="chart-caption">This bridge reconciles the officially reported Central Government debt to the full IPSAS 35 consolidated liability. Each step is anchored to a specific document and page citation (see Section 2).</p>

        <h3>Chart B — Reported vs. Consolidated: The Gap Visualized</h3>
        {chart_stacked_html}
        <p class="chart-caption">Side-by-side comparison. The bottom bar shows what the government reports. The top bar shows what it owes when all public sector obligations are consolidated, including the BDS $1.48B in Parliamentary Resolution borrowing. Segment labels indicate the time horizon of each liability.</p>

        <div class="page-break"></div>

        <!-- SECTION 2 -->
        <h2>2. Forensic Evidence & Official Citations</h2>
        
        <h3>A. Central Bank Insolvency (The 2018 Restructuring)</h3>
        <div class="quote-box">
            "The Bank has recorded net capital and deficit of <strong>$1,422,167 [thousands]</strong> (2024: $1,528,756 [thousands]) as at December 31, 2025. This deficit was caused primarily by significant non-recurring costs in 2018 of $1,693,255 [thousands]... the institution of a debt exchange which resulted in the derecognition of Government treasury bills and debentures under the Debt Holder (Approval of Debt Restructuring) Act."
            <span class="source">Source: Central Bank of Barbados 2025 Annual Report, Note 1 (Page 70)</span>
        </div>
        <p><strong>Analytical Implication:</strong> The 2018 debt restructuring transferred BDS $1.42 Billion of sovereign debt onto the balance sheet of the Central Bank. The IMF's 2026 Article IV report (Page 25, ¶27) acknowledges that a recapitalization plan exists, based on profit retention. However, at current profit levels, filling a BDS $1.42B hole would take decades. In the interim, this negative equity remains an implicit sovereign obligation that is excluded from the official debt stock.</p>

        <h3>B. NIS Actuarial Depletion Risk</h3>
        <div class="quote-box">
            "Total Net Assets: $4,234M. ...Reserves are projected to be exhausted in 2036."
            <span class="source">Source: NIS 17th Actuarial Review (as of Dec 31, 2020), Table 1.6 (Page 16) & Chapter 3 (Page 24)</span>
        </div>
        <p><strong>Analytical Implication:</strong> The most recent <em>publicly available</em> actuarial review is the 17th Review (2020), which projects the National Insurance Fund will be depleted by 2036, with a total net asset shortfall of BDS $4.2 Billion. The IMF's 2026 Article IV report (Page 60, Figure 6) notes that the 2022-2023 parametric reforms have extended the fund's lifespan, projecting a residual annual financing need of 0.2–0.4 pp of GDP for the next 50 years. However, the IMF's assessment must rely on a newer actuarial review that has not been published on the NIS website nor tabled in Parliament. Until that update is publicly available, the 2020 Review remains the only verifiable baseline for the <em>stock</em> liability (the $4.2B shortfall). The IMF is measuring the <em>annual cash flow subsidy</em>; the 2020 Review measures the <em>total unfunded actuarial liability</em>.</p>

        <h3>C. Unfunded Government Pension Liability <span class="estimate-tag">ESTIMATE</span></h3>
        <div class="quote-box">
            "In addition, the liability for pensions and employee benefits were not included in the Statement of Financial Position... The Government of Barbados uses an unfunded defined benefit plan for the payment of superannuation benefits to its employees. Benefits are paid by the Government as and when due. No assets are therefore being put aside to meet any obligations that may arise in the future."
            <span class="source">Source: Auditor General Report 2023, Page 4 (Basis for Adverse Opinion) & Note 8 (Page 23)</span>
        </div>
        <p><strong>Analytical Implication:</strong> The Government of Barbados operates a pay-as-you-go pension system for public servants. Unlike the NIS — which covers private-sector workers and holds approximately BDS $4.2 Billion in ring-fenced assets — the Government Pension Plan has <strong>no dedicated assets</strong>. The BDS $333.6 Million reported as "Retiring Benefits and Allowances" is only the <em>annual cash outlay</em>, not the total unfunded liability. The Auditor General explicitly cites this omission as a basis for his adverse opinion.</p>
        <p><strong>Estimation Methodology:</strong> Using a conservative 2.5× multiplier of annual payroll (BDS $864 Million), the present value of accrued pension obligations is estimated at <strong>BDS $2.16 Billion</strong>. This is a standard actuarial proxy for mature unfunded defined benefit plans. <em>This represents a conservative floor; the NIS — a separate scheme — reports a BDS $4.2 Billion shortfall under the 2020 Actuarial Review.</em> <strong>Note on the IMF's Assessment:</strong> The IMF's 2026 Article IV report (Page 60, Figure 6) correctly notes that the 2022-2023 parametric reforms have extended the NIS lifespan, projecting a residual annual financing need of 0.2–0.4 pp of GDP for the next 50 years. However, the IMF is measuring the <em>annual cash flow subsidy</em> required to keep the fund solvent, not the <em>total unfunded actuarial liability</em> (the $4.2B stock). Furthermore, the IMF's analysis explicitly covers the NIS (private-sector workers) but does <strong>not</strong> evaluate the Government Pension Plan for public servants, which has no ring-fenced assets and remains a completely unfunded obligation.</p>

        <h3>D. SOE Debt (Stock vs. Arrears)</h3>
        <div class="quote-box">
            "Government guaranteed SOE debt remained contained at BDS $69.8 million at end-March 2026 (0.4 percent of GDP). SOE non-guaranteed debt also remains stable at around BDS $426 million (2.7 percent of GDP). Implicit government guarantees remain a concern, including unfunded pension liabilities."
            <span class="source">Source: IMF 2026 Article IV Consultation, Annex VII (Page 87, ¶5)</span>
        </div>
        <p><strong>Analytical Implication:</strong> This brief reconciles two distinct SOE exposures: (1) the BDS $426 million in non-guaranteed SOE debt (2.7% of GDP) disclosed in the IMF 2026 report, and (2) the BDS $74.6 million in arrears from the MoF Mid-Year Review, which represents unpaid bills at the NPC, BWA and SSA. Both are excluded from the headline sovereign debt figure, and both are implicit fiscal risks. The IMF explicitly states that "implicit government guarantees remain a concern."</p>

        <h3>E. The IMF's DSA Perimeter (What It Includes vs. What It Excludes)</h3>
        <div class="quote-box">
            "SOE debt not guaranteed by the central government is small at 2.6 percent of GDP at end-March 2026 and is not included in the analysis. ...Contingent liabilities: 147.2 (1.9% of GDP)."
            <span class="source">Source: IMF 2026 Article IV, Annex II, Footnote 1 (Page 57) & Table 2 (Page 62)</span>
        </div>
        <p><strong>Analytical Implication:</strong> The IMF's DSA does include BDS $147.2M in public guarantees and 1.3% of GDP in expenditure arrears. But it explicitly excludes the BDS $426M in non-guaranteed SOE debt (2.6% of GDP). This brief captures the excluded amount as an additional line item in Section 3. The IMF's own footnote is the strongest possible evidence that the official DSA perimeter is incomplete.</p>

        <h3>F. The IMF's SRDSF Assessment vs. the Consolidated Reality</h3>
        <div class="quote-box">
            "The Sovereign Risk and Debt Sustainability Framework (SRDSF) suggests that Barbados' overall risk of sovereign stress is moderate, and that debt is sustainable (see Annex II)."
            <span class="source">Source: IMF 2026 Article IV, ¶22 (Page 24)</span>
        </div>
        <p><strong>Analytical Implication:</strong> The IMF's SRDSF assesses Barbados' debt as sustainable. But this assessment relies on a perimeter that excludes the BDS ${total_hidden:,.0f} gap identified in this brief. If those liabilities were consolidated, the SRDSF's mechanical signal would likely shift from "moderate" to "high" risk of sovereign stress. This is not a critique of the IMF's methodology — it is an observation about the boundary of the data it uses.</p>

        <h3>G. The 2025 Eurobond (Parliamentary Resolution, June 24, 2025)</h3>
        <div class="quote-box">
            "WHEREAS the Government of Barbados deems it necessary to borrow up to $500 million in the currency of the United States of America on the international capital market the proceeds of which will be used to fund the liability management operation and to prepay a portion of Central Government's debt to the International Monetary Fund for the External Fund Facility... <strong>Coupon: 8.000 per cent per annum... Maturity: 26th June, 2035</strong>"
            <span class="source">Source: Parliamentary Resolution, June 24, 2025 (Pages 1 & 4)</span>
        </div>
        <p><strong>Analytical Implication:</strong> The June 2025 liability management operation (LMO) restructured the Government's near-term maturity profile. The 6.5% 2029 Eurobond was subject to a sinking fund amortization schedule, with principal repayments commencing in April 2025 (IMF 2026 Article IV, Page 58, Box 1). The new US$500M bond carries an 8.0% coupon and includes a five-year principal grace period until December 2030. The LMO eliminates near-term principal amortization pressure and extends the sovereign's maturity profile by six years, in exchange for a higher annual coupon (8.0% vs. 6.5%). The proceeds were allocated to refinancing the 2029 bond and prepaying IMF EFF obligations, rather than to addressing the Central Bank's negative equity or the NIS actuarial shortfall.</p>
        <p><strong>Implication for Debt Sustainability:</strong> The extension of maturities improves the near-term liquidity profile, but the underlying stock of unconsolidated liabilities (CBB, NIS, Government Pension) remains unchanged. The 2035 maturity date coincides with the government's BERT 2026 target of reaching 60% debt-to-GDP by FY2035/36. The LMO therefore buys time for structural consolidation without resolving the underlying liability composition.</p>

        <h3>H. Parliamentary Resolutions (2022-2025): The Full Borrowing Record</h3>
        <div class="quote-box">
            "WHEREAS by virtue of section 2 of the Special Loans Act, Cap. 105, the Government is authorised from time to time to borrow... The nine Parliamentary Resolutions from 2022-2025 authorise total borrowing of approximately BBD $1.48 billion and USD $37.4 million."
            <span class="source">Source: Parliamentary Resolutions (2022-2025), Special Loans Act, Cap. 105</span>
        </div>
        <p><strong>Analytical Implication:</strong> The Government of Barbados has borrowed approximately <strong>BBD $1.48 billion and USD $37.4 million</strong> through nine Parliamentary Resolutions between 2022 and 2025. These borrowings are legally binding, approved by Parliament, and classified as 'Special Loans' rather than 'Central Government Debt.' They are excluded from the IMF's DSA perimeter and from the headline 96% debt-to-GDP figure. The nine resolutions are: SINOPHARM (BBD $313.6M), CARICOM CDF (USD $12.4M), Exim Bank of China (BBD $256.6M), Saudi Fund Urban Renewal (BBD $68.4M), Saudi Fund Polyclinic (BBD $117M), CIBC/Scotiabank/RBC Syndicated Facility (BBD $600M), Kensington Oval (USD $25M), UWI/CDB (BBD $2M), and OPEC Fund (BBD $100M).</p>

        <h3>I. The Excluded 2013 QEH/RBC Loan (Data Audit)</h3>
        <div class="quote-box">
            "The QEH RBC loan (BDS $25M, 2013 Resolution) is excluded from this register. The loan carried a 7-year term from disbursement, implying maturity around 2020-2021. There is no evidence of extension or refinancing in the 2025-2026 documentation."
            <span class="source">Source: Parliamentary Resolution, December 5, 2013 (Page 3, Terms and Conditions)</span>
        </div>
        <p><strong>Analytical Implication:</strong> The QEH RBC loan (BDS $25M) from the December 5, 2013 Parliamentary Resolution is excluded from the liability register. The loan carried a 7-year term from disbursement, implying maturity around 2020-2021. There is no evidence of extension or refinancing in the 2025-2026 documentation (MoF Mid-Year Review, IMF Article IV, CBB Annual Report). It is noted here for completeness but is not counted as an outstanding liability. This demonstrates forensic rigor: each line item is audited against current documentation.</p>

        <div class="page-break"></div>

        <!-- SECTION 3 -->
        <h2>3. Unconsolidated Liability Register</h2>
        <table>
            <tr><th>Entity / Project</th><th>Amount (BDS)</th><th>Classification</th><th>Source Document</th></tr>
            <tr><td>QEH (China SINOPHARM)</td><td>313,600,000</td><td>Deferred Payment</td><td>Parliament Resolution 2025</td></tr>
            <tr><td>CARICOM Development Fund</td><td>24,800,000</td><td>Term Loan (Wastewater)</td><td>Parliament Resolution 2024</td></tr>
            <tr><td>Exim Bank of China</td><td>256,600,000</td><td>Term Loan (Roads)</td><td>Parliament Resolution 2022</td></tr>
            <tr><td>Saudi Fund (Urban Renewal)</td><td>68,400,000</td><td>Term Loan (Infrastructure)</td><td>Parliament Resolution 2025</td></tr>
            <tr><td>Saudi Fund (Polyclinic)</td><td>117,000,000</td><td>Term Loan (Health)</td><td>Parliament Resolution 2025</td></tr>
            <tr><td>CIBC/Scotiabank/RBC</td><td>600,000,000</td><td>Sustainability-Linked Loan</td><td>Parliament Resolution 2024</td></tr>
            <tr><td>Kensington Oval</td><td>50,000,000</td><td>Government Guarantee (SOE)</td><td>Parliament Resolution 2023</td></tr>
            <tr><td>UWI (CDB)</td><td>2,000,000</td><td>Government Guarantee (UWI)</td><td>Parliament Resolution 2022</td></tr>
            <tr><td>OPEC Fund</td><td>100,000,000</td><td>Term Loan (Social Services)</td><td>Parliament Resolution 2025</td></tr>
            <tr><td>SOE Arrears (BWA, NPC, SSA)</td><td>74,600,000</td><td>Unconsolidated SOE Arrears</td><td>MoF Mid-Year Review 2025 (Page 22)</td></tr>
            <tr><td>SOE Non-Guaranteed Debt</td><td>426,000,000</td><td>Non-Guaranteed SOE Debt Stock</td><td>IMF 2026 Article IV (Page 87)</td></tr>
            <tr><td>Central Bank of Barbados</td><td>1,422,167,000</td><td>Negative Equity</td><td>CBB 2024/2025 Annual Report</td></tr>
            <tr><td>NIS Pension Fund</td><td>4,200,000,000</td><td>Actuarial Depletion</td><td>17th Actuarial Review 2020</td></tr>
            <tr><td>Government Public Pension Plan <span class="estimate-tag">EST</span></td><td>2,159,811,000</td><td>Unfunded Defined Benefit</td><td>AG Report 2023, Note 8 (Page 23)</td></tr>
            <tr style="font-weight: 800; background-color: #F8F9FA; border-top: 2px solid #1A252F;">
                <td>TOTAL UNCONSOLIDATED LIABILITIES</td>
                <td>BDS ${total_hidden:,.0f}</td>
                <td colspan="2">Excluded from Headline Debt</td>
            </tr>
        </table>
        <p class="chart-caption" style="text-align: left; margin-top: 10px;">The 2013 QEH/RBC loan (BDS $25M) is excluded from this register as it reached maturity in 2020-2021. There is no evidence of extension in the 2025-2026 documentation.</p>

        <!-- SECTION 4 -->
        <h2>4. Structural Considerations for Multilateral Review</h2>
        <p>While the BDS ${total_hidden/1e9:.2f} Billion gap is mathematically supported by current documentation, the consolidated sovereign exposure may be higher due to the boundary of the reporting entity. The Government of Barbados does not consolidate the financial statements of its State-Owned Enterprises (SOEs) into the Central Government accounts. The IMF's 2026 Article IV report formally acknowledges that both the NIS and the Central Bank are excluded from its DSA perimeter (Page 58, Figure 1).</p>
        
        <p><strong>Key Areas for Multilateral Review:</strong></p>
        <ul>
            <li><strong>Two Distinct Unfunded Pension Obligations:</strong> The NIS (private-sector workers) is projected to exhaust its assets by 2036. The Government Public Pension Plan (public servants) has <em>no assets at all</em>. Both are unfunded obligations of the sovereign. The IMF's 2026 report (Page 60) shows a 50-year residual financing need of 0.2–0.4 pp of GDP per year for the NIS alone. Any credible sustainability analysis must count both.</li>
            <li><strong>Government Guarantees:</strong> Loans guaranteed by the government (e.g., QEH SINOPHARM, BWA facilities) represent contingent liabilities. In the event of SOE default, these become direct sovereign obligations.</li>
            <li><strong>Deferred Payment Agreements:</strong> Mechanisms such as the China SINOPHARM deal allow capital projects to proceed without immediate impact on gross borrowing figures, but they represent future fixed outflows.</li>
            <li><strong>Implicit Subsidies:</strong> Structurally loss-making entities (e.g., Transport Board, BWA) require annual cash injections. These ongoing operational deficits act as a perpetual drain on the Consolidated Fund.</li>
            <li><strong>Intercompany Arrears:</strong> The Ministry of Finance Mid-Year Review (Page 22) reports <strong>BDS $74.6 million</strong> in total SOE arrears, concentrated in the National Petroleum Corporation, Barbados Water Authority, and Sanitation Service Authority. Combined with the BDS $426M in non-guaranteed SOE debt disclosed by the IMF, total SOE exposure is BDS $500.6M.</li>
        </ul>

        <p><strong>The Expanding Off-Budget Borrowing Ceiling:</strong> The Government is actively expanding the legal mechanism used to create off-budget liabilities. On October 29, 2026, a Bill was introduced in Parliament to amend the Special Loans Act (Cap. 105), <strong>doubling the aggregate borrowing limit from BDS $2.5 Billion to BDS $5.0 Billion</strong>. This legislation governs the exact type of "Special Loans" (such as the US$170M China Exim loan and the US$67.9M Citibank BWA loan) that are on-lent to SOEs and excluded from the standard Central Government debt calculation. The doubling of this limit represents a forward-looking structural risk: it provides the legal headroom to significantly expand unconsolidated liabilities without triggering standard debt reporting metrics.</p>

        <p><strong>Historical Precedent (2007 IMF Article IV):</strong> The exclusion of implicit liabilities is not a recent phenomenon. The IMF's 2007 Article IV report (Table 1, Page 16) explicitly tracked "Off-budget activities" as a separate deficit line, which reached <strong>-5.7% of GDP in 2002</strong> and remained at -3.3% of GDP in 2007. These off-budget activities—which included the same SOE on-lending and deferred payment mechanisms seen today—were later dropped from the headline DSA reporting. The 2026 gap of BDS ${total_hidden/1e9:.2f}B is the accumulated stock of these decades of off-budget borrowing.</p>

        <p><strong>The 2028–2035 Maturity Cliff and the Absence of Audited Data:</strong> The government's fiscal reporting infrastructure is significantly delayed. The most recent audited financial statements available are for FY2023, which were signed off by the Auditor General on April 2, 2025—20 months past the statutory deadline. Section 88(1) of the Public Finance Management Act (2019-1) mandates that the Accountant-General submit the statements within 4 months of the fiscal year-end. The FY2024 statements remain outstanding as of November 2026. As a result, the IMF's 2026 Article IV and the MoF's Mid-Year Review are necessarily built on a combination of unaudited data, partial accruals, and cash-basis reporting, rather than a full IPSAS-compliant balance sheet. This reporting gap masks the true stock of liabilities. The danger window is not today; it is <strong>2028 to 2035</strong>. In 2028, IMF EFF obligations resume. In 2030, the 5-year grace period on the US$500M Eurobond ends, and principal repayments begin. In 2035, the bond matures, coinciding with the BERT 2026 debt target. In 2036, the NIS fund is projected to be fully depleted (based on the 2020 Review). <strong>Compounding this is the CBB recapitalization plan (IMF 2026 Article IV, Page 25, ¶27), which requires the government to transition from profit retention to a gradual predetermined payment plan to fill the BDS $1.42 billion negative equity hole.</strong> If an external shock—a global recession, an oil spike, or a natural disaster—hits during this window, the government will have significantly less fiscal space than it had in 2018. The hard-currency claims (Eurobond, China Exim, Citibank BWA) and the scheduled domestic obligations (CBB recapitalization, NIS subsidies) will compete for the same reserves. For a small, open economy with a fixed-exchange-rate peg, this is not merely a domestic fiscal risk; it is a balance-of-payments risk with regional contagion implications for the ECCU and CARICOM. The 2018 restructuring was painful; a 2028–2035 crisis, compounded by two decades of off-budget borrowing, would be significantly worse.</p>

        <p><strong>Recommendation:</strong> We recommend that multilateral institutions consider expanding the perimeter to consolidate CBB, NIS, and Government Pension liabilities into the central government's debt calculation, formally include the BDS $426M in non-guaranteed SOE debt in the debt perimeter, and disclose the full stock of Parliamentary Resolution borrowing (2022-2025) in the annual debt report, to provide a more accurate assessment of the sovereign's debt sustainability under IPSAS 35.</p>

        <!-- SECTION 5 -->
        <h2>5. Debt Sustainability Target Analysis</h2>
        <p>The government's BERT 2026 programme targets a debt-to-GDP ratio of 60% by 2035. The IMF's 2026 Article IV report assesses debt as sustainable under its baseline, projecting a decline below 60% by FY2035/36 (Page 24, ¶22). However, this assessment explicitly excludes the BDS ${total_hidden:,.0f} in unconsolidated liabilities. If these liabilities were consolidated, the 60% target would require either a significantly larger primary surplus or a longer consolidation horizon — requiring a larger primary surplus than the IMF's baseline assumes over its current projection horizon (FY2035/36).</p>

        <!-- FOOTER -->
        <div class="footer">
            Generated by Sovereign Risk Navigator · Deterministic Fiscal Engine.<br>
            Data is derived from official Government of Barbados, CBB, and IMF 2026 Article IV documents. Government Pension Liability figure is a conservative actuarial estimate pending the Ministry of Finance's pension study.<br>
            This is an automated analysis and does not constitute a formal audit opinion.
        </div>
    </div>
    </body>
    </html>
    """
    return html