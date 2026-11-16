# Sovereign Risk Navigator: Barbados

A deterministic forensic extraction and calculation engine that quantifies unconsolidated public sector liabilities under **IPSAS 35 (Consolidated Financial Statements)**.

## The Core Thesis
Governments in small, open economies systematically exclude implicit liabilities from their official debt figures to maintain the appearance of solvency. This engine reconciles the Government of Barbados' reported 96.0% debt-to-GDP ratio against the IMF's 2026 Article IV DSA perimeter, calculating a **True Consolidated Debt-to-GDP ratio of 155.2%** (a BDS $9.81 Billion gap).

## Architecture
*   `data/sovereign_state.json`: Structured liability data (auto-populated).
*   `navigator/true_debt.py`: Core IPSAS 35 consolidation calculator.
*   `navigator/peg_defense.py`: External sector stress test (12-week reserve benchmark).
*   `dashboard.py`: Interactive Streamlit dashboard with Plotly visualizations.
*   `report_generator.py`: Institutional HTML/PDF brief generator with full forensic citations.

## Usage
To run the interactive dashboard locally:
```bash
pip install -r requirements.txt
streamlit run dashboard.py
