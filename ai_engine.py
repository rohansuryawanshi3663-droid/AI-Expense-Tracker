"""Lightweight, explainable AI-style insights for the expense tracker.

This module works without API keys or paid AI services. Category suggestions use
keyword scoring; spending insights use transparent rules over the user's data.
"""

import pandas as pd

CATEGORY_KEYWORDS = {
    "Food": ["food", "lunch", "dinner", "breakfast", "restaurant", "canteen", "pizza", "burger", "coffee", "tea", "snack", "swiggy", "zomato"],
    "Transport": ["bus", "train", "metro", "auto", "rickshaw", "taxi", "uber", "ola", "petrol", "fuel", "parking"],
    "Shopping": ["shirt", "shoes", "clothes", "shopping", "amazon", "flipkart", "mall", "watch"],
    "Bills": ["electricity", "water bill", "internet", "wifi", "mobile recharge", "recharge", "bill", "gas"],
    "Education": ["college", "book", "books", "course", "exam", "stationery", "notebook", "tuition", "fees"],
    "Health": ["doctor", "medicine", "hospital", "pharmacy", "health", "gym", "clinic"],
    "Entertainment": ["movie", "cinema", "netflix", "game", "gaming", "concert", "subscription"],
    "Travel": ["hotel", "flight", "trip", "holiday", "resort", "booking"],
    "Groceries": ["grocery", "groceries", "vegetable", "vegetables", "milk", "rice", "atta", "supermarket", "fruits"],
}

def suggest_category(description):
    text = (description or "").lower()
    scores = {}
    for category, words in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for word in words if word in text)
    if not scores or max(scores.values(), default=0) == 0:
        return "Other"
    return max(scores, key=scores.get)

def build_spending_insights(df, budget=0, today=None):
    insights = []
    if df is None or df.empty:
        return ["Start by adding expenses. As your data grows, this page will identify categories that take the largest share of your spending."]
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce").fillna(0)
    data = data.dropna(subset=["date"])
    if data.empty:
        return ["Add valid dated expenses to generate insights."]
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    month_data = data[(data["date"].dt.year == today.year) & (data["date"].dt.month == today.month)]
    month_total = float(month_data["amount"].sum())
    if not month_data.empty:
        cat = month_data.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_category = str(cat.index[0])
        top_amount = float(cat.iloc[0])
        share = (top_amount / month_total * 100) if month_total else 0
        insights.append(f"**Largest category this month:** {top_category} accounts for ₹{top_amount:,.2f} ({share:.0f}% of this month's spending).")
        if len(cat) >= 2:
            second = str(cat.index[1])
            insights.append(f"Your next-largest category is **{second}**. Review both categories first if you want to reduce spending.")
        daily = month_data.groupby(month_data["date"].dt.date)["amount"].sum()
        if len(daily) >= 2:
            biggest_day = daily.idxmax()
            insights.append(f"Your highest-spending day this month was **{biggest_day.strftime('%d %b %Y')}**, with ₹{daily.max():,.2f} recorded.")
    else:
        insights.append("There are no expenses recorded for the current month yet.")
    if budget and budget > 0:
        ratio = month_total / budget
        if ratio > 1:
            insights.append(f"**Budget alert:** you are ₹{month_total-budget:,.2f} over your monthly budget. Consider pausing non-essential purchases for the rest of the month.")
        elif ratio >= 0.8:
            insights.append(f"**Budget alert:** you've used {ratio*100:.0f}% of your budget. There is ₹{max(budget-month_total,0):,.2f} remaining.")
        else:
            insights.append(f"You have used {ratio*100:.0f}% of your monthly budget, leaving ₹{budget-month_total:,.2f}.")
    if len(data) >= 5:
        recent = data.sort_values("date")
        monthly = recent.groupby(recent["date"].dt.to_period("M"))["amount"].sum()
        if len(monthly) >= 2:
            prev, current = float(monthly.iloc[-2]), float(monthly.iloc[-1])
            if prev > 0:
                change = (current - prev) / prev * 100
                if change > 10:
                    insights.append(f"Recorded spending is **{change:.0f}% higher** in the latest month than the previous month. The latest month may be incomplete.")
                elif change < -10:
                    insights.append(f"Recorded spending is **{abs(change):.0f}% lower** in the latest month than the previous month. Nice progress, if both months are comparable.")
                else:
                    insights.append("Your latest month's spending is broadly similar to the previous month, based on the records entered.")
    essentials = {"Bills", "Education", "Health", "Groceries", "Transport", "Food"}
    nonessential_total = float(data.loc[~data["category"].isin(essentials), "amount"].sum())
    all_total = float(data["amount"].sum())
    if all_total > 0:
        share = nonessential_total / all_total * 100
        insights.append(f"Across all recorded transactions, categories outside the basic essentials list make up about **{share:.0f}%** of spending. Check the category labels to ensure this comparison is meaningful for you.")
    return insights

def predict_next_month(df, today=None):
    if df is None or df.empty:
        return None
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce").fillna(0)
    data = data.dropna(subset=["date"])
    if data.empty:
        return None
    monthly = data.groupby(data["date"].dt.to_period("M"))["amount"].sum().tail(3)
    if len(monthly) == 0:
        return None
    return float(monthly.mean())
