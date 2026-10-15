import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "expenses.db"

def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                payment_method TEXT NOT NULL DEFAULT 'Other',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                month TEXT PRIMARY KEY,
                amount REAL NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
    _import_existing_csv_if_needed()

def _import_existing_csv_if_needed():
    """Import a repository expenses.csv once if the SQLite table is empty."""
    csv_path = Path(__file__).resolve().parent / "expenses.csv"
    if not csv_path.exists():
        return
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        if count:
            return
        try:
            source = pd.read_csv(csv_path)
        except Exception:
            return
        if source.empty:
            return
        normalized = {str(c).strip().lower().replace(" ", "_"): c for c in source.columns}
        def find_column(*names):
            for name in names:
                if name in normalized:
                    return normalized[name]
            return None
        date_col = find_column("date", "expense_date", "transaction_date")
        amount_col = find_column("amount", "expense", "cost", "price")
        category_col = find_column("category", "type")
        description_col = find_column("description", "title", "name", "expense_name", "item")
        payment_col = find_column("payment_method", "payment", "method")
        notes_col = find_column("notes", "note", "remarks")
        if date_col is None or amount_col is None:
            return
        for _, row in source.iterrows():
            try:
                parsed_date = pd.to_datetime(row[date_col], errors="raise").date().isoformat()
                amount = float(row[amount_col])
                if amount <= 0:
                    continue
                category = str(row[category_col]) if category_col and pd.notna(row[category_col]) else "Other"
                description = str(row[description_col]) if description_col and pd.notna(row[description_col]) else category
                payment = str(row[payment_col]) if payment_col and pd.notna(row[payment_col]) else "Other"
                notes = str(row[notes_col]) if notes_col and pd.notna(row[notes_col]) else ""
                conn.execute(
                    "INSERT INTO expenses (date, amount, category, description, payment_method, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    (parsed_date, amount, category, description, payment, notes)
                )
            except Exception:
                continue
        conn.commit()

def add_expense(expense_date, amount, category, description, payment_method, notes=""):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO expenses (date, amount, category, description, payment_method, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (expense_date, float(amount), category, description, payment_method, notes)
        )
        conn.commit()

def get_expenses():
    with _connect() as conn:
        return pd.read_sql_query(
            "SELECT id, date, amount, category, description, payment_method, notes FROM expenses ORDER BY date DESC, id DESC",
            conn
        )

def get_all_expenses():
    return get_expenses()

def update_expense(expense_id, expense_date, amount, category, description, payment_method, notes=""):
    with _connect() as conn:
        conn.execute(
            """UPDATE expenses SET date=?, amount=?, category=?, description=?, payment_method=?, notes=?
               WHERE id=?""",
            (expense_date, float(amount), category, description, payment_method, notes, int(expense_id))
        )
        conn.commit()

def delete_expense(expense_id):
    with _connect() as conn:
        conn.execute("DELETE FROM expenses WHERE id=?", (int(expense_id),))
        conn.commit()

def get_monthly_budget(month):
    with _connect() as conn:
        row = conn.execute("SELECT amount FROM budgets WHERE month=?", (month,)).fetchone()
        return float(row["amount"]) if row else 0.0

def set_monthly_budget(month, amount):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO budgets (month, amount) VALUES (?, ?)
               ON CONFLICT(month) DO UPDATE SET amount=excluded.amount""",
            (month, float(amount))
        )
        conn.commit()
