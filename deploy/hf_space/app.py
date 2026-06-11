from __future__ import annotations

import random
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


DB_PATH = Path("/tmp/datatalk_company.sqlite")


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    rows: list[dict[str, Any]]
    answer: str
    route: str
    confidence: float
    latency_ms: float
    mode: str


app = FastAPI(title="DataTalk API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db() -> None:
    if DB_PATH.exists():
        return

    rng = random.Random(42)
    conn = connect()
    conn.executescript(
        """
        CREATE TABLE customers (
          customer_id INTEGER PRIMARY KEY,
          customer_name TEXT NOT NULL,
          segment TEXT NOT NULL,
          region TEXT NOT NULL,
          industry TEXT NOT NULL
        );

        CREATE TABLE products (
          product_id INTEGER PRIMARY KEY,
          product_name TEXT NOT NULL,
          category TEXT NOT NULL,
          list_price REAL NOT NULL
        );

        CREATE TABLE sales_orders (
          order_id INTEGER PRIMARY KEY,
          order_date TEXT NOT NULL,
          customer_id INTEGER NOT NULL,
          product_id INTEGER NOT NULL,
          region TEXT NOT NULL,
          channel TEXT NOT NULL,
          quantity INTEGER NOT NULL,
          unit_price REAL NOT NULL,
          discount_pct REAL NOT NULL
        );

        CREATE TABLE support_tickets (
          ticket_id INTEGER PRIMARY KEY,
          opened_date TEXT NOT NULL,
          customer_id INTEGER NOT NULL,
          product_id INTEGER,
          priority TEXT NOT NULL,
          status TEXT NOT NULL,
          sentiment_score INTEGER NOT NULL,
          issue_type TEXT NOT NULL
        );

        CREATE TABLE employees (
          employee_id INTEGER PRIMARY KEY,
          employee_name TEXT NOT NULL,
          department TEXT NOT NULL,
          region TEXT NOT NULL,
          status TEXT NOT NULL
        );

        CREATE TABLE invoices (
          invoice_id INTEGER PRIMARY KEY,
          customer_id INTEGER NOT NULL,
          invoice_date TEXT NOT NULL,
          due_date TEXT NOT NULL,
          amount REAL NOT NULL,
          status TEXT NOT NULL
        );
        """
    )

    regions = ["North", "South", "East", "West", "Central"]
    segments = ["enterprise", "mid-market", "smb"]
    industries = ["Healthcare", "Finance", "Retail", "Manufacturing", "Education"]
    products = [
        ("DataTalk Core", "Analytics", 1200.0),
        ("DataTalk Pro", "Analytics", 2400.0),
        ("Insight Desk", "Support", 900.0),
        ("Forecast API", "Finance", 1500.0),
        ("Retention Radar", "Customer Success", 1800.0),
    ]
    departments = ["Engineering", "Sales", "Support", "Finance", "HR"]

    for i in range(1, 81):
        conn.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
            (i, f"Customer {i:03d}", rng.choice(segments), rng.choice(regions), rng.choice(industries)),
        )

    for i, product in enumerate(products, start=1):
        conn.execute("INSERT INTO products VALUES (?, ?, ?, ?)", (i, *product))

    order_id = 1
    for year in [2025, 2026]:
        months = range(1, 13) if year == 2025 else range(1, 4)
        for month in months:
            for _ in range(95):
                customer_id = rng.randint(1, 80)
                product_id = rng.randint(1, len(products))
                region = conn.execute(
                    "SELECT region FROM customers WHERE customer_id = ?", (customer_id,)
                ).fetchone()["region"]
                quantity = rng.randint(1, 12)
                unit_price = products[product_id - 1][2] * rng.uniform(0.85, 1.15)
                discount_pct = rng.choice([0, 0.03, 0.05, 0.08, 0.12])
                conn.execute(
                    "INSERT INTO sales_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        order_id,
                        f"{year}-{month:02d}-{rng.randint(1, 28):02d}",
                        customer_id,
                        product_id,
                        region,
                        rng.choice(["direct", "partner", "web"]),
                        quantity,
                        round(unit_price, 2),
                        discount_pct,
                    ),
                )
                order_id += 1

    for i in range(1, 321):
        conn.execute(
            "INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                i,
                f"{rng.choice([2025, 2026])}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                rng.randint(1, 80),
                rng.randint(1, len(products)),
                rng.choice(["low", "medium", "high", "critical"]),
                rng.choice(["open", "in_progress", "closed"]),
                rng.randint(1, 5),
                rng.choice(["billing", "bug", "onboarding", "performance", "training"]),
            ),
        )

    for i in range(1, 61):
        conn.execute(
            "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
            (
                i,
                f"Employee {i:03d}",
                rng.choice(departments),
                rng.choice(regions),
                rng.choice(["active", "active", "active", "left"]),
            ),
        )

    for i in range(1, 501):
        year = rng.choice([2025, 2026])
        month = rng.randint(1, 12 if year == 2025 else 3)
        day = rng.randint(1, 28)
        conn.execute(
            "INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?)",
            (
                i,
                rng.randint(1, 80),
                f"{year}-{month:02d}-{day:02d}",
                f"{year}-{month:02d}-{min(day + 14, 28):02d}",
                round(rng.uniform(800, 28000), 2),
                rng.choice(["paid", "paid", "open", "void"]),
            ),
        )

    conn.commit()
    conn.close()


def date_filter(question: str, column: str) -> str:
    q = question.lower()
    if "q1" in q or "quarter 1" in q:
        return f"{column} BETWEEN '2026-01-01' AND '2026-03-31'"
    if "q2" in q:
        return f"{column} BETWEEN '2025-04-01' AND '2025-06-30'"
    if "q3" in q:
        return f"{column} BETWEEN '2025-07-01' AND '2025-09-30'"
    if "q4" in q:
        return f"{column} BETWEEN '2025-10-01' AND '2025-12-31'"
    if "2026" in q:
        return f"{column} BETWEEN '2026-01-01' AND '2026-12-31'"
    return f"{column} BETWEEN '2025-01-01' AND '2025-12-31'"


def compile_sql(question: str) -> tuple[str, str, float]:
    q = question.lower()
    sales_date = date_filter(question, "order_date")
    ticket_date = date_filter(question, "opened_date")
    invoice_date = date_filter(question, "due_date")

    if "revenue" in q and "region" in q:
        return (
            "revenue_by_region",
            f"""
            SELECT region, ROUND(SUM(quantity * unit_price * (1 - discount_pct)), 2) AS revenue
            FROM sales_orders
            WHERE {sales_date}
            GROUP BY region
            ORDER BY revenue DESC
            """,
            0.96,
        )
    if ("top product" in q or "top products" in q or "best product" in q) and "revenue" in q:
        return (
            "top_products",
            f"""
            SELECT p.product_name, p.category,
                   ROUND(SUM(s.quantity * s.unit_price * (1 - s.discount_pct)), 2) AS revenue,
                   SUM(s.quantity) AS units_sold
            FROM sales_orders s
            JOIN products p ON p.product_id = s.product_id
            WHERE {sales_date}
            GROUP BY p.product_id, p.product_name, p.category
            ORDER BY revenue DESC
            LIMIT 10
            """,
            0.96,
        )
    if "customer" in q and ("spend" in q or "sales" in q or "revenue" in q):
        return (
            "customer_revenue",
            f"""
            SELECT c.customer_name, c.segment, c.region,
                   ROUND(SUM(s.quantity * s.unit_price * (1 - s.discount_pct)), 2) AS revenue
            FROM sales_orders s
            JOIN customers c ON c.customer_id = s.customer_id
            WHERE {sales_date}
            GROUP BY c.customer_id, c.customer_name, c.segment, c.region
            ORDER BY revenue DESC
            LIMIT 15
            """,
            0.96,
        )
    if "churn" in q or ("risk" in q and "ticket" in q):
        return (
            "churn_risk_tickets",
            f"""
            SELECT c.customer_name, c.segment, c.region,
                   COUNT(*) AS risky_ticket_count,
                   MIN(t.sentiment_score) AS worst_sentiment,
                   GROUP_CONCAT(DISTINCT t.issue_type) AS issue_types
            FROM support_tickets t
            JOIN customers c ON c.customer_id = t.customer_id
            WHERE {ticket_date}
              AND t.status != 'closed'
              AND (t.priority IN ('high', 'critical') OR t.sentiment_score <= 2)
            GROUP BY c.customer_id, c.customer_name, c.segment, c.region
            ORDER BY risky_ticket_count DESC, worst_sentiment ASC
            LIMIT 15
            """,
            0.96,
        )
    if "ticket" in q:
        return (
            "tickets_by_status_priority",
            f"""
            SELECT status, priority, COUNT(*) AS ticket_count, ROUND(AVG(sentiment_score), 2) AS avg_sentiment
            FROM support_tickets
            WHERE {ticket_date}
            GROUP BY status, priority
            ORDER BY ticket_count DESC
            """,
            0.96,
        )
    if "attrition" in q or ("employee" in q and ("left" in q or "turnover" in q)):
        return (
            "attrition_by_department",
            """
            SELECT department, COUNT(*) AS employees_left
            FROM employees
            WHERE status = 'left'
            GROUP BY department
            ORDER BY employees_left DESC
            """,
            0.96,
        )
    if "overdue" in q or ("invoice" in q and "open" in q):
        return (
            "overdue_invoices",
            f"""
            SELECT c.customer_name, c.segment, c.region,
                   COUNT(*) AS overdue_invoice_count,
                   ROUND(SUM(i.amount), 2) AS overdue_amount
            FROM invoices i
            JOIN customers c ON c.customer_id = i.customer_id
            WHERE {invoice_date}
              AND i.status = 'open'
              AND i.due_date < '2026-04-01'
            GROUP BY c.customer_id, c.customer_name, c.segment, c.region
            ORDER BY overdue_amount DESC
            LIMIT 15
            """,
            0.96,
        )
    if "monthly" in q or "trend" in q:
        return (
            "monthly_revenue_trend",
            f"""
            SELECT SUBSTR(order_date, 1, 7) AS month,
                   ROUND(SUM(quantity * unit_price * (1 - discount_pct)), 2) AS revenue,
                   COUNT(*) AS order_count
            FROM sales_orders
            WHERE {sales_date}
            GROUP BY month
            ORDER BY month
            """,
            0.96,
        )
    return (
        "fallback_sales_summary",
        f"""
        SELECT SUBSTR(order_date, 1, 7) AS month, region,
               ROUND(SUM(quantity * unit_price * (1 - discount_pct)), 2) AS revenue,
               COUNT(*) AS order_count
        FROM sales_orders
        WHERE {sales_date}
        GROUP BY month, region
        ORDER BY month, revenue DESC
        LIMIT 25
        """,
        0.72,
    )


def validate_select(sql: str) -> str:
    cleaned = " ".join(sql.strip().split())
    lowered = cleaned.lower()
    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "attach", "detach", "pragma"]
    if not lowered.startswith("select "):
        raise ValueError("Only SELECT queries are allowed.")
    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")
    if any(f" {word} " in f" {lowered} " for word in forbidden):
        raise ValueError("Unsafe SQL keyword found.")
    return cleaned


def run_query(sql: str) -> list[dict[str, Any]]:
    ensure_db()
    cleaned = validate_select(sql)
    if " limit " not in cleaned.lower():
        cleaned = f"{cleaned} LIMIT 200"
    with connect() as conn:
        rows = conn.execute(cleaned).fetchall()
        return [dict(row) for row in rows]


def summarize(route: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No matching rows were found."
    first = rows[0]
    if route == "revenue_by_region":
        return f"Top region is {first['region']} with revenue {first['revenue']:.2f}."
    if route == "top_products":
        return f"Top product is {first['product_name']} with revenue {first['revenue']:.2f}."
    if route == "customer_revenue":
        return f"Top customer is {first['customer_name']} with revenue {first['revenue']:.2f}."
    if route == "churn_risk_tickets":
        return f"Highest churn-risk customer is {first['customer_name']} with {first['risky_ticket_count']} risky ticket(s)."
    if route == "tickets_by_status_priority":
        return f"Largest ticket bucket is {first['status']} / {first['priority']} with {first['ticket_count']} ticket(s)."
    if route == "attrition_by_department":
        return f"Highest attrition is in {first['department']} with {first['employees_left']} employee(s) left."
    if route == "overdue_invoices":
        return f"Largest overdue exposure is {first['customer_name']} with {first['overdue_amount']:.2f}."
    if route == "monthly_revenue_trend":
        return f"Returned {len(rows)} monthly revenue point(s)."
    return f"Returned {len(rows)} row(s)."


@app.on_event("startup")
def startup() -> None:
    ensure_db()


@app.get("/health")
def health() -> dict[str, Any]:
    ensure_db()
    return {"ok": True, "mode": "compiler_api", "database": DB_PATH.exists()}


@app.get("/examples")
def examples() -> dict[str, list[str]]:
    return {
        "questions": [
            "Show revenue by region for 2025",
            "Top products by revenue for Q1",
            "Top customers by spend for 2026",
            "Find churn risk tickets for Q4",
            "Show open support tickets by priority",
            "Employee attrition by department",
            "Show overdue invoices",
            "Show monthly revenue trend for 2025",
        ]
    }


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    started = time.perf_counter()
    route, sql, confidence = compile_sql(request.question)
    cleaned_sql = validate_select(sql)
    rows = run_query(cleaned_sql)
    latency_ms = (time.perf_counter() - started) * 1000
    return QueryResponse(
        question=request.question,
        sql=cleaned_sql,
        rows=rows,
        answer=summarize(route, rows),
        route=route,
        confidence=confidence,
        latency_ms=latency_ms,
        mode="compiler_api",
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>DataTalk</title>
        <style>
          :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
          body { margin: 0; background: #f5f7fa; color: #111827; }
          main { max-width: 1120px; margin: 0 auto; padding: 32px 20px; }
          h1 { margin: 0 0 6px; font-size: 32px; letter-spacing: 0; }
          p { color: #4b5563; line-height: 1.5; }
          .toolbar { display: flex; gap: 8px; margin: 18px 0; flex-wrap: wrap; }
          button, input { font: inherit; }
          input { flex: 1; min-width: 280px; padding: 12px 14px; border: 1px solid #cbd5e1; border-radius: 6px; background: white; }
          button { padding: 11px 14px; border: 1px solid #1f2937; border-radius: 6px; background: #1f2937; color: white; cursor: pointer; }
          button.secondary { background: white; color: #1f2937; border-color: #cbd5e1; }
          .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 0.8fr); gap: 16px; align-items: start; }
          section { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
          pre { white-space: pre-wrap; overflow: auto; background: #0f172a; color: #e5e7eb; padding: 14px; border-radius: 6px; }
          table { width: 100%; border-collapse: collapse; font-size: 13px; }
          th, td { border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }
          th { background: #f8fafc; }
          .meta { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 12px; }
          .pill { border: 1px solid #d1d5db; border-radius: 999px; padding: 4px 8px; font-size: 12px; color: #374151; background: #f9fafb; }
          @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
        </style>
      </head>
      <body>
        <main>
          <h1>DataTalk</h1>
          <p>Ask supported company data questions and inspect the compiled SQL, source rows, route, confidence, and latency.</p>
          <div class="toolbar">
            <input id="question" value="Show revenue by region for 2025" />
            <button onclick="runQuery()">Run</button>
            <button class="secondary" onclick="loadExample()">Example</button>
          </div>
          <div class="grid">
            <section>
              <h2>Answer</h2>
              <div class="meta" id="meta"></div>
              <p id="answer">Run a query to see the grounded answer.</p>
              <h3>Rows</h3>
              <div id="rows"></div>
            </section>
            <section>
              <h2>SQL</h2>
              <pre id="sql"></pre>
            </section>
          </div>
        </main>
        <script>
          const examples = [
            "Show revenue by region for 2025",
            "Top products by revenue for Q1",
            "Top customers by spend for 2026",
            "Find churn risk tickets for Q4",
            "Show overdue invoices",
            "Show monthly revenue trend for 2025"
          ];
          function loadExample() {
            const q = examples[Math.floor(Math.random() * examples.length)];
            document.getElementById("question").value = q;
          }
          function renderRows(rows) {
            if (!rows.length) return "<p>No rows.</p>";
            const cols = Object.keys(rows[0]);
            return `<table><thead><tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>` +
              rows.map(r => `<tr>${cols.map(c => `<td>${String(r[c])}</td>`).join("")}</tr>`).join("") +
              "</tbody></table>";
          }
          async function runQuery() {
            const question = document.getElementById("question").value;
            const response = await fetch("/query", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({question})
            });
            const data = await response.json();
            document.getElementById("answer").textContent = data.answer;
            document.getElementById("sql").textContent = data.sql;
            document.getElementById("rows").innerHTML = renderRows(data.rows);
            document.getElementById("meta").innerHTML = [
              `route: ${data.route}`,
              `confidence: ${data.confidence}`,
              `latency: ${data.latency_ms.toFixed(1)} ms`,
              `mode: ${data.mode}`
            ].map(x => `<span class="pill">${x}</span>`).join("");
          }
          runQuery();
        </script>
      </body>
    </html>
    """
