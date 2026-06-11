from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import DB_PATH
from .data import connect, ensure_db
from .intent_compiler import compile_question
from .router import QueryPlan, route_question
from .sql_guard import ensure_limit, validate_read_only_select


@dataclass
class QueryResponse:
    question: str
    sql: str
    rows: list[dict[str, Any]]
    answer: str
    confidence: float
    route: str
    rationale: str
    latency_ms: float


def execute_sql(sql: str, db_path: Path = DB_PATH, limit: int = 200) -> list[dict[str, Any]]:
    ensure_db(db_path)
    guarded_sql = ensure_limit(sql, limit=limit)
    conn = connect(db_path)
    try:
        cursor = conn.execute(guarded_sql)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def summarize_rows(plan: QueryPlan, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No matching rows were found for this question."

    first = rows[0]
    if plan.route == "revenue_by_region":
        return f"Top region is {first['region']} with revenue {first['revenue']:.2f}."
    if plan.route == "top_products":
        return f"Top product is {first['product_name']} with revenue {first['revenue']:.2f} and {first['units_sold']} units sold."
    if plan.route == "customer_revenue":
        return f"Top customer is {first['customer_name']} with revenue {first['revenue']:.2f}."
    if plan.route == "churn_risk_tickets":
        return f"Highest churn-risk customer is {first['customer_name']} with {first['risky_ticket_count']} risky open ticket(s)."
    if plan.route == "tickets_by_status_priority":
        return f"Largest ticket bucket is {first['status']} / {first['priority']} with {first['ticket_count']} ticket(s)."
    if plan.route == "attrition_by_department":
        return f"Highest attrition is in {first['department']} with {first['employees_left']} employee(s) left."
    if plan.route == "overdue_invoices":
        return f"Largest overdue exposure is {first['customer_name']} with {first['overdue_amount']:.2f} overdue."
    if plan.route == "monthly_revenue_trend":
        return f"Returned {len(rows)} monthly revenue point(s)."
    return f"Returned {len(rows)} row(s). Review the SQL and table for the grounded answer."


def answer_question(
    question: str,
    db_path: Path = DB_PATH,
    sql: str | None = None,
    mode: str = "compiler",
) -> QueryResponse:
    start = time.perf_counter()
    if sql:
        guarded = validate_read_only_select(sql)
        plan = QueryPlan(sql=guarded, confidence=0.7, route="model_generated_sql", rationale="SQL came from the trained model path.")
    elif mode == "router":
        plan = route_question(question)
    else:
        plan = compile_question(question)

    rows = execute_sql(plan.sql, db_path=db_path)
    latency_ms = (time.perf_counter() - start) * 1000
    return QueryResponse(
        question=question,
        sql=validate_read_only_select(plan.sql),
        rows=rows,
        answer=summarize_rows(plan, rows),
        confidence=plan.confidence,
        route=plan.route,
        rationale=plan.rationale,
        latency_ms=latency_ms,
    )


def assert_db_queryable(db_path: Path = DB_PATH) -> None:
    ensure_db(db_path)
    conn = connect(db_path)
    try:
        conn.execute("SELECT COUNT(*) FROM customers").fetchone()
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(f"DataTalk database is not queryable: {db_path}") from exc
    finally:
        conn.close()
