import io
from datetime import date, datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    init_db, add_expense, get_expenses, update_expense, delete_expense,
    get_monthly_budget, set_monthly_budget, get_all_expenses
)
from ai_engine import suggest_category, build_spending_insights, predict_next_month

st.set_page_config(
    page_title="AI Expense Tracker",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px;}
    [data-testid="stMetric"] {background: linear-gradient(135deg, #f8fafc, #eef2ff); padding: 16px 18px; border-radius: 16px; border: 1px solid #e2e8f0;}
    [data-testid="stMetricLabel"] {font-weight: 600;}
    .hero {padding: 1.3rem 1.5rem; border-radius: 20px; background: linear-gradient(120deg,#111827,#3730a3); color: white; margin-bottom: 1.2rem;}
    .hero h1 {color:white; margin:0; font-size:2rem;}
    .hero p {color:#e0e7ff; margin:.4rem 0 0 0;}
    .small-muted {color:#64748b; font-size:.9rem;}
    div.stButton > button {border-radius: 10px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Education", "Health", "Entertainment", "Travel", "Groceries", "Other"]
PAYMENT_METHODS = ["UPI", "Cash", "Card", "Bank Transfer", "Other"]

st.sidebar.title("💸 Expense Tracker")
st.sidebar.caption("Track spending. Understand habits. Stay on budget.")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Expense", "Manage Expenses", "Budget & AI Insights", "Reports"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption("Your data is stored in this app's local SQLite database. For a public demo, avoid entering sensitive financial information.")

def money(value):
    return f"₹{float(value):,.2f}"

def month_key(d):
    return pd.Timestamp(d).strftime("%Y-%m")

def load_data():
    df = get_expenses()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"])
    return df

def current_month_data(df):
    if df.empty:
        return df
    today = date.today()
    return df[(df["date"].dt.year == today.year) & (df["date"].dt.month == today.month)]

df = load_data()
today = date.today()
this_month = current_month_data(df)
budget = get_monthly_budget(month_key(today))

if page == "Dashboard":
    st.markdown(f"""
    <div class="hero">
      <h1>💸 AI Expense Tracker</h1>
      <p>Your personal finance command centre · {today.strftime('%B %Y')}</p>
    </div>
    """, unsafe_allow_html=True)

    total_all = float(df["amount"].sum()) if not df.empty else 0
    total_month = float(this_month["amount"].sum()) if not this_month.empty else 0
    avg_expense = float(df["amount"].mean()) if not df.empty else 0
    largest = float(df["amount"].max()) if not df.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spent this month", money(total_month))
    c2.metric("All-time spending", money(total_all))
    c3.metric("Average transaction", money(avg_expense))
    c4.metric("Largest transaction", money(largest))

    if budget > 0:
        used_pct = min(total_month / budget, 1.5) * 100
        st.subheader("Monthly budget")
        st.progress(min(total_month / budget, 1.0))
        st.write(f"Used **{used_pct:.1f}%** of your {money(budget)} budget · Remaining: **{money(max(budget-total_month, 0))}**")
        if total_month > budget:
            st.error(f"Budget exceeded by {money(total_month-budget)}.")
        elif total_month >= budget * 0.8:
            st.warning("You've used at least 80% of your monthly budget.")
    else:
        st.info("Set a monthly budget in **Budget & AI Insights** to track how you are doing.")

    left, right = st.columns(2)
    with left:
        st.subheader("Spending by category")
        if not this_month.empty:
            cat = this_month.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            fig = px.pie(cat, names="category", values="amount", hole=0.58, title="This month")
            fig.update_layout(margin=dict(t=50,b=10,l=10,r=10), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expenses this month yet. Add your first expense to see category charts.")
    with right:
        st.subheader("Daily spending trend")
        if not this_month.empty:
            daily = this_month.groupby(this_month["date"].dt.date, as_index=False)["amount"].sum()
            daily.columns = ["date", "amount"]
            fig = px.line(daily, x="date", y="amount", markers=True, title="Daily totals", labels={"date":"Date","amount":"Amount (₹)"})
            fig.update_layout(margin=dict(t=50,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Your daily trend will appear here after you add expenses.")

    st.subheader("Recent expenses")
    if not df.empty:
        recent = df.sort_values(["date", "id"], ascending=[False, False]).head(8).copy()
        recent["date"] = recent["date"].dt.strftime("%d %b %Y")
        recent["amount"] = recent["amount"].map(money)
        st.dataframe(recent[["date","description","category","payment_method","amount"]], use_container_width=True, hide_index=True)
    else:
        st.info("No expenses recorded yet. Choose **Add Expense** from the sidebar to get started.")

elif page == "Add Expense":
    st.title("➕ Add an expense")
    st.caption("Record a transaction. The category suggestion is generated from the description.")
    with st.form("add_expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            expense_date = st.date_input("Date", value=today, max_value=date(2100, 12, 31))
            amount = st.number_input("Amount (₹)", min_value=0.01, max_value=100000000.0, value=100.0, step=10.0, format="%.2f")
            description = st.text_input("Description", placeholder="e.g. lunch at college canteen")
        with col2:
            suggested = suggest_category(description) if description.strip() else "Other"
            category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(suggested) if suggested in CATEGORIES else CATEGORIES.index("Other"))
            payment_method = st.selectbox("Payment method", PAYMENT_METHODS)
            notes = st.text_input("Notes (optional)", placeholder="Any extra details")
        if description.strip():
            st.caption(f"Suggested category: **{suggested}** · You can change it before saving.")
        submitted = st.form_submit_button("Save expense", type="primary", use_container_width=True)
        if submitted:
            if not description.strip():
                st.error("Please enter a description.")
            else:
                add_expense(expense_date.isoformat(), amount, category, description.strip(), payment_method, notes.strip())
                st.success("Expense saved successfully.")
                st.rerun()

elif page == "Manage Expenses":
    st.title("🧾 Manage expenses")
    st.caption("Edit or delete a transaction. Changes update your dashboard and reports.")
    if df.empty:
        st.info("No expenses to manage yet.")
    else:
        search = st.text_input("Search description or category")
        filtered = df.copy()
        if search.strip():
            mask = (
                filtered["description"].astype(str).str.contains(search, case=False, na=False)
                | filtered["category"].astype(str).str.contains(search, case=False, na=False)
            )
            filtered = filtered[mask]
        display = filtered.sort_values(["date","id"], ascending=[False,False]).copy()
        display["date"] = display["date"].dt.strftime("%Y-%m-%d")
        display["amount"] = display["amount"].map(lambda x: f"{x:.2f}")
        st.dataframe(display[["id","date","description","category","amount","payment_method","notes"]], use_container_width=True, hide_index=True)

        ids = filtered["id"].astype(int).tolist()
        if ids:
            selected_id = st.selectbox("Choose expense ID to edit or delete", ids, format_func=lambda x: f"#{x} · {filtered.loc[filtered['id']==x, 'description'].iloc[0]}")
            item = filtered[filtered["id"] == selected_id].iloc[0]
            with st.expander("✏️ Edit selected expense", expanded=True):
                with st.form("edit_expense_form"):
                    e1, e2 = st.columns(2)
                    with e1:
                        edit_date = st.date_input("Date", value=item["date"].date(), key="edit_date")
                        edit_amount = st.number_input("Amount (₹)", min_value=0.01, value=float(item["amount"]), step=10.0, key="edit_amount")
                        edit_description = st.text_input("Description", value=str(item["description"]), key="edit_description")
                    with e2:
                        old_cat = str(item["category"])
                        edit_category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(old_cat) if old_cat in CATEGORIES else CATEGORIES.index("Other"), key="edit_category")
                        old_pay = str(item["payment_method"])
                        edit_payment = st.selectbox("Payment method", PAYMENT_METHODS, index=PAYMENT_METHODS.index(old_pay) if old_pay in PAYMENT_METHODS else PAYMENT_METHODS.index("Other"), key="edit_payment")
                        edit_notes = st.text_input("Notes", value=str(item.get("notes", "") or ""), key="edit_notes")
                    save_edit = st.form_submit_button("Save changes", type="primary")
                    if save_edit:
                        if not edit_description.strip():
                            st.error("Description cannot be empty.")
                        else:
                            update_expense(int(selected_id), edit_date.isoformat(), edit_amount, edit_category, edit_description.strip(), edit_payment, edit_notes.strip())
                            st.success("Expense updated.")
                            st.rerun()
            with st.expander("🗑️ Delete selected expense"):
                st.warning(f"This will permanently delete '{item['description']}' (ID {selected_id}).")
                confirm = st.checkbox("I understand this expense will be deleted.", key="confirm_delete")
                if st.button("Delete expense", type="primary", disabled=not confirm):
                    delete_expense(int(selected_id))
                    st.success("Expense deleted.")
                    st.rerun()

elif page == "Budget & AI Insights":
    st.title("🧠 Budget & AI spending insights")
    st.caption("Understand your patterns and catch budget issues early.")
    current_key = month_key(today)
    with st.form("budget_form"):
        current_budget = get_monthly_budget(current_key)
        new_budget = st.number_input("Set this month's budget (₹)", min_value=0.0, value=float(current_budget), step=500.0)
        save_budget = st.form_submit_button("Save monthly budget", type="primary")
        if save_budget:
            set_monthly_budget(current_key, new_budget)
            st.success(f"Budget saved for {today.strftime('%B %Y')}.")
            st.rerun()

    total_month = float(this_month["amount"].sum()) if not this_month.empty else 0
    budget = get_monthly_budget(current_key)
    if budget > 0:
        ratio = total_month / budget
        st.progress(min(ratio, 1.0))
        st.metric("Budget remaining", money(max(budget-total_month, 0)), delta=f"{ratio*100:.1f}% used")
        if ratio > 1:
            st.error(f"You are over budget by {money(total_month-budget)}.")
        elif ratio >= 0.8:
            st.warning("Budget alert: you've spent 80% or more of your monthly limit.")
        else:
            st.success("You are currently within your budget.")
    else:
        st.info("Set a budget above to activate monthly budget alerts.")

    st.subheader("AI spending insights")
    insights = build_spending_insights(df, budget=budget, today=today)
    if insights:
        for insight in insights:
            st.markdown(f"- {insight}")
    else:
        st.info("Add a few expenses to unlock personalized spending insights.")

    prediction = predict_next_month(df, today=today)
    if prediction is not None:
        st.subheader("Next-month estimate")
        st.metric("Estimated spending", money(prediction))
        st.caption("This is a simple trend-based estimate from your recorded monthly totals, not a guarantee.")

elif page == "Reports":
    st.title("📊 Reports & downloads")
    st.caption("Filter your records and download them for Excel or your project report.")
    if df.empty:
        st.info("Add expenses first to generate a report.")
    else:
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        r1, r2 = st.columns(2)
        with r1:
            start_date = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date)
        with r2:
            end_date = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date)
        if start_date > end_date:
            st.error("The start date must be before the end date.")
            report = pd.DataFrame()
        else:
            report = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)].copy()
        if not report.empty:
            total = report["amount"].sum()
            st.metric("Report total", money(total), delta=f"{len(report)} transactions")
            category_report = report.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            st.plotly_chart(px.bar(category_report, x="category", y="amount", title="Spend by category", labels={"category":"Category","amount":"Amount (₹)"}), use_container_width=True)
            export_df = report.copy()
            export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")
            csv_bytes = export_df[["id","date","amount","category","description","payment_method","notes"]].to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Download expenses CSV", data=csv_bytes, file_name=f"expense_report_{start_date}_{end_date}.csv", mime="text/csv", use_container_width=True)
            summary = category_report.copy()
            summary["period_start"] = str(start_date)
            summary["period_end"] = str(end_date)
            summary_csv = summary.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Download category summary CSV", data=summary_csv, file_name=f"category_summary_{start_date}_{end_date}.csv", mime="text/csv", use_container_width=True)
            st.dataframe(export_df[["date","description","category","amount","payment_method"]], use_container_width=True, hide_index=True)
        else:
            st.info("No expenses found in this date range.")
