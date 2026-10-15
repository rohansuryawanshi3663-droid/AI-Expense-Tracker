# AI Expense Tracker

A responsive Streamlit mini-project for recording expenses, exploring spending patterns, setting a monthly budget, and downloading reports.

## Features
- Add, edit, and delete expenses
- Dashboard KPIs and interactive Plotly charts
- Keyword-based expense category suggestion
- Rule-based, explainable spending insights
- Monthly budget alerts at 80% and over-budget levels
- Trend-based next-month estimate
- CSV download for transactions and category summaries

## Tech stack
- Python
- Streamlit
- SQLite
- Pandas
- Plotly

## Run locally
1. Install Python 3.10 or later.
2. Open a terminal in this folder.
3. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud
1. Push these files to your GitHub repository.
2. Open https://share.streamlit.io/
3. Choose **Create app** / deploy an existing repository.
4. Repository: `rohansuryawanshi3663-droid/AI-Expense-Tracker`
5. Branch: `main`
6. Main file path: `app.py`
7. Click **Deploy**.

## Important data note
This demo stores expenses and budgets in a local SQLite database (`expenses.db`). On hosted platforms, local files may not be durable across app restarts, rebuilds, or redeployments. Do not use this demo as a production financial record system or enter sensitive account details. For durable multi-user storage, connect a hosted database.

## About the "AI" features
Category suggestions and spending insights are lightweight, explainable heuristics that run locally without an external AI API or API key. The next-month figure is a simple average of recent monthly totals, not a guaranteed prediction.
