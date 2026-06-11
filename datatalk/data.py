from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from .config import DB_PATH, ensure_artifact_dirs
from .schema import DDL, INDEX_DDL


REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["startup", "mid-market", "enterprise"]
INDUSTRIES = ["healthcare", "finance", "retail", "manufacturing", "education", "software"]
CHANNELS = ["direct", "partner", "marketplace", "inside_sales"]
DEPARTMENTS = ["sales", "engineering", "support", "finance", "hr", "marketing", "operations"]
PRIORITIES = ["low", "medium", "high", "critical"]
TICKET_STATUSES = ["open", "pending", "closed"]
ISSUE_TYPES = ["billing", "bug", "onboarding", "performance", "feature_request", "security"]

PRODUCTS = [
    ("Atlas CRM", "sales", 129.0),
    ("Pulse Desk", "support", 89.0),
    ("LedgerFlow", "finance", 149.0),
    ("PeopleGraph", "hr", 99.0),
    ("MetricHub", "analytics", 179.0),
    ("SecureVault", "security", 199.0),
    ("CampaignOS", "marketing", 119.0),
    ("OpsPilot", "operations", 139.0),
]

FIRST_NAMES = [
    "Aarav",
    "Anika",
    "Dev",
    "Isha",
    "Kabir",
    "Mira",
    "Neel",
    "Riya",
    "Vihaan",
    "Zara",
    "Arjun",
    "Diya",
]
COMPANY_SUFFIXES = ["Labs", "Systems", "Works", "Cloud", "Group", "Digital", "Analytics"]


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _date_between(rng: random.Random, start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, delta))


def _executemany(conn: sqlite3.Connection, sql: str, rows: Iterable[tuple]) -> None:
    conn.executemany(sql, list(rows))


def init_db(db_path: Path = DB_PATH, overwrite: bool = False, seed: int = 7) -> Path:
    ensure_artifact_dirs()
    if overwrite and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    conn = connect(db_path)
    with conn:
        conn.executescript(DDL)
        conn.executescript(INDEX_DDL)

        _executemany(
            conn,
            "INSERT INTO products(product_id, product_name, category, list_price) VALUES (?, ?, ?, ?)",
            [(i + 1, *product) for i, product in enumerate(PRODUCTS)],
        )

        customer_rows = []
        for customer_id in range(1, 181):
            company = f"{rng.choice(FIRST_NAMES)} {rng.choice(COMPANY_SUFFIXES)}"
            customer_rows.append(
                (
                    customer_id,
                    company,
                    rng.choices(SEGMENTS, weights=[0.35, 0.4, 0.25], k=1)[0],
                    rng.choice(REGIONS),
                    rng.choice(INDUSTRIES),
                    _date_between(rng, date(2021, 1, 1), date(2025, 12, 31)).isoformat(),
                )
            )
        _executemany(
            conn,
            """
            INSERT INTO customers(customer_id, customer_name, segment, region, industry, joined_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            customer_rows,
        )

        employee_rows = []
        for employee_id in range(1, 96):
            status = rng.choices(["active", "left"], weights=[0.84, 0.16], k=1)[0]
            hire_date = _date_between(rng, date(2019, 1, 1), date(2025, 12, 31))
            left_date = None
            if status == "left":
                left_start = max(hire_date + timedelta(days=120), date(2025, 1, 1))
                left_end = date(2026, 3, 31)
                if left_start > left_end:
                    left_start = hire_date + timedelta(days=30)
                    left_end = hire_date + timedelta(days=180)
                left_date = _date_between(rng, left_start, left_end).isoformat()
            employee_rows.append(
                (
                    employee_id,
                    f"{rng.choice(FIRST_NAMES)} {rng.choice(['Shah', 'Patel', 'Singh', 'Mehta', 'Dave'])}",
                    rng.choice(DEPARTMENTS),
                    rng.choice(REGIONS),
                    hire_date.isoformat(),
                    status,
                    left_date,
                    rng.choice(["A", "B", "C"]),
                )
            )
        _executemany(
            conn,
            """
            INSERT INTO employees(employee_id, employee_name, department, region, hire_date, status, left_date, performance_band)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            employee_rows,
        )

        sales_rows = []
        invoice_rows = []
        for order_id in range(1, 2601):
            customer = rng.choice(customer_rows)
            product_id, _, _, list_price = rng.choice([(i + 1, *product) for i, product in enumerate(PRODUCTS)])
            order_date = _date_between(rng, date(2025, 1, 1), date(2026, 3, 31))
            quantity = rng.randint(1, 18)
            discount = rng.choice([0.0, 0.0, 0.05, 0.1, 0.15, 0.2])
            unit_price = round(list_price * rng.uniform(0.92, 1.08), 2)
            amount = round(quantity * unit_price * (1 - discount), 2)
            sales_rows.append(
                (
                    order_id,
                    order_date.isoformat(),
                    customer[0],
                    product_id,
                    customer[3],
                    rng.choice(CHANNELS),
                    quantity,
                    unit_price,
                    discount,
                )
            )

            due_date = order_date + timedelta(days=30)
            is_paid = rng.random() > 0.16
            paid_date = (due_date - timedelta(days=rng.randint(0, 20))).isoformat() if is_paid else None
            invoice_rows.append(
                (
                    order_id,
                    customer[0],
                    order_date.isoformat(),
                    due_date.isoformat(),
                    paid_date,
                    amount,
                    "paid" if is_paid else "open",
                )
            )

        _executemany(
            conn,
            """
            INSERT INTO sales_orders(order_id, order_date, customer_id, product_id, region, channel, quantity, unit_price, discount_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sales_rows,
        )
        _executemany(
            conn,
            """
            INSERT INTO invoices(invoice_id, customer_id, invoice_date, due_date, paid_date, amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            invoice_rows,
        )

        ticket_rows = []
        for ticket_id in range(1, 851):
            customer = rng.choice(customer_rows)
            opened = _date_between(rng, date(2025, 1, 1), date(2026, 3, 31))
            status = rng.choices(TICKET_STATUSES, weights=[0.18, 0.19, 0.63], k=1)[0]
            closed_date = None
            if status == "closed":
                closed_date = (opened + timedelta(days=rng.randint(1, 18))).isoformat()
            priority = rng.choices(PRIORITIES, weights=[0.34, 0.38, 0.21, 0.07], k=1)[0]
            sentiment = rng.choices([1, 2, 3, 4, 5], weights=[0.08, 0.16, 0.34, 0.28, 0.14], k=1)[0]
            ticket_rows.append(
                (
                    ticket_id,
                    opened.isoformat(),
                    closed_date,
                    customer[0],
                    rng.randint(1, len(PRODUCTS)),
                    priority,
                    status,
                    sentiment,
                    rng.choice(ISSUE_TYPES),
                )
            )
        _executemany(
            conn,
            """
            INSERT INTO support_tickets(ticket_id, opened_date, closed_date, customer_id, product_id, priority, status, sentiment_score, issue_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ticket_rows,
        )

    conn.close()
    return db_path


def table_counts(db_path: Path = DB_PATH) -> dict[str, int]:
    conn = connect(db_path)
    try:
        tables = ["customers", "products", "sales_orders", "support_tickets", "employees", "invoices"]
        return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
    finally:
        conn.close()


def ensure_db(db_path: Path = DB_PATH) -> Path:
    if not db_path.exists():
        init_db(db_path=db_path, overwrite=False)
    return db_path
