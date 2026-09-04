import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from pathlib import Path

DATA_FILE = Path("data/expenses.csv")

st.set_page_config(page_title="AI Expense Tracker", page_icon="💰", layout="wide")

CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Education", "Health", "Entertainment", "Other"]

def load_data():
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])

def save_data(df):
    DATA_FILE.parent.mkdir(exist_ok=True)
    df.to_csv(DATA_FILE, index=False)

st.title("💰 AI Expense Tracker")
st.caption("A simple Python + Streamlit dashboard for tracking and analysing personal expenses.")

df = load_data()

with st.sidebar:
    st.header("➕ Add Expense")
    expense_date = st.date_input("Date", date.today())
    category = st.selectbox("Category", CATEGORIES)
    description = st.text_input("Description")
    amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0)

    if st.button("Add Expense", use_container_width=True):
        if amount > 0:
            new_row = pd.DataFrame([{
                "Date": str(expense_date),
                "Category": category,
                "Description": description or "Expense",
                "Amount": amount
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("Expense added!")
            st.rerun()
        else:
            st.warning("Enter an amount greater than ₹0.")

if df.empty:
    st.info("No expenses yet. Add your first expense using the sidebar.")
else:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    total = df["Amount"].sum()
    average = df["Amount"].mean()
    highest = df["Amount"].max()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Spending", f"₹{total:,.0f}")
    c2.metric("Average Expense", f"₹{average:,.0f}")
    c3.metric("Highest Expense", f"₹{highest:,.0f}")

    st.divider()

    left, right = st.columns(2)

    with left:
        by_category = df.groupby("Category", as_index=False)["Amount"].sum()
        fig = px.pie(by_category, names="Category", values="Amount",
                     title="Spending by Category", hole=0.35)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        daily = df.groupby("Date", as_index=False)["Amount"].sum()
        fig = px.line(daily, x="Date", y="Amount", markers=True,
                      title="Daily Spending")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Expense History")
    st.dataframe(df.sort_values("Date", ascending=False),
                 use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "expenses.csv", "text/csv")

    st.subheader("🤖 Simple AI-style Insights")
    category_totals = df.groupby("Category")["Amount"].sum()
    top_category = category_totals.idxmax()
    top_amount = category_totals.max()

    st.write(f"• Your highest spending category is **{top_category}** (₹{top_amount:,.0f}).")
    if total > 0 and top_amount / total >= 0.40:
        st.warning(f"More than 40% of your recorded spending is in {top_category}. Consider setting a budget for it.")
    else:
        st.success("Your spending is reasonably distributed across the recorded categories.")
