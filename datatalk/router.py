from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryPlan:
    sql: str
    confidence: float
    route: str
    rationale: str


def _date_filter(question: str, column: str) -> str:
    q = question.lower()
    if "q1" in q or "quarter 1" in q:
        return f"{column} BETWEEN '2026-01-01' AND '2026-03-31'"
    if "q4" in q:
        return f"{column} BETWEEN '2025-10-01' AND '2025-12-31'"
    if "q3" in q:
        return f"{column} BETWEEN '2025-07-01' AND '2025-09-30'"
    if "q2" in q:
        return f"{column} BETWEEN '2025-04-01' AND '2025-06-30'"
    if "2026" in q:
        return f"{column} BETWEEN '2026-01-01' AND '2026-12-31'"
    if "2025" in q or "last year" in q:
        return f"{column} BETWEEN '2025-01-01' AND '2025-12-31'"
    return f"{column} BETWEEN '2025-01-01' AND '2026-03-31'"


def route_question(question: str) -> QueryPlan:
    q = question.lower().strip()
    sales_date = _date_filter(q, "order_date")
    ticket_date = _date_filter(q, "opened_date")
    invoice_date = _date_filter(q, "due_date")

    if "revenue" in q and "region" in q:
        return QueryPlan(
            sql=f"""
            SELECT region,
                   ROUND(SUM(quantity * unit_price * (1 - discount_pct)), 2) AS revenue
            FROM sales_orders
            WHERE {sales_date}
            GROUP BY region
            ORDER BY revenue DESC
            """,
            confidence=0.92,
            route="revenue_by_region",
            rationale="Matched revenue and region; revenue is computed from sales_orders.",
        )

    if ("top" in q or "best" in q) and ("product" in q or "products" in q):
        return QueryPlan(
            sql=f"""
            SELECT p.product_name,
                   p.category,
                   ROUND(SUM(s.quantity * s.unit_price * (1 - s.discount_pct)), 2) AS revenue,
                   SUM(s.quantity) AS units_sold
            FROM sales_orders s
            JOIN products p ON p.product_id = s.product_id
            WHERE {sales_date}
            GROUP BY p.product_id, p.product_name, p.category
            ORDER BY revenue DESC
            LIMIT 10
            """,
            confidence=0.9,
            route="top_products",
            rationale="Matched top product query; ranks products by computed revenue.",
        )

    if "customer" in q and ("revenue" in q or "spend" in q or "sales" in q):
        return QueryPlan(
            sql=f"""
            SELECT c.customer_name,
                   c.segment,
                   c.region,
                   ROUND(SUM(s.quantity * s.unit_price * (1 - s.discount_pct)), 2) AS revenue
            FROM sales_orders s
            JOIN customers c ON c.customer_id = s.customer_id
            WHERE {sales_date}
            GROUP BY c.customer_id, c.customer_name, c.segment, c.region
            ORDER BY revenue DESC
            LIMIT 15
            """,
            confidence=0.86,
            route="customer_revenue",
            rationale="Matched customer revenue query; joins customers to sales_orders.",
        )

    if "churn" in q or ("risk" in q and "ticket" in q):
        return QueryPlan(
            sql=f"""
            SELECT c.customer_name,
                   c.segment,
                   c.region,
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
            confidence=0.88,
            route="churn_risk_tickets",
            rationale="Matched churn/risk ticket query using the business definition.",
        )

    if "ticket" in q and ("priority" in q or "open" in q or "status" in q):
        return QueryPlan(
            sql=f"""
            SELECT status,
                   priority,
                   COUNT(*) AS ticket_count,
                   ROUND(AVG(sentiment_score), 2) AS avg_sentiment
            FROM support_tickets
            WHERE {ticket_date}
            GROUP BY status, priority
            ORDER BY ticket_count DESC
            """,
            confidence=0.84,
            route="tickets_by_status_priority",
            rationale="Matched ticket status/priority aggregation.",
        )

    if "attrition" in q or ("employee" in q and ("left" in q or "turnover" in q)):
        return QueryPlan(
            sql="""
            SELECT department,
                   COUNT(*) AS employees_left
            FROM employees
            WHERE status = 'left'
            GROUP BY department
            ORDER BY employees_left DESC
            """,
            confidence=0.86,
            route="attrition_by_department",
            rationale="Matched attrition; attrition is employees with status left.",
        )

    if "overdue" in q or ("invoice" in q and "open" in q):
        return QueryPlan(
            sql=f"""
            SELECT c.customer_name,
                   c.segment,
                   c.region,
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
            confidence=0.88,
            route="overdue_invoices",
            rationale="Matched overdue/open invoice query.",
        )

    if "monthly" in q or "trend" in q:
        return QueryPlan(
            sql=f"""
            SELECT SUBSTR(order_date, 1, 7) AS month,
                   ROUND(SUM(quantity * unit_price * (1 - discount_pct)), 2) AS revenue,
                   COUNT(*) AS order_count
            FROM sales_orders
            WHERE {sales_date}
            GROUP BY month
            ORDER BY month
            """,
            confidence=0.82,
            route="monthly_revenue_trend",
            rationale="Matched monthly trend; groups sales by YYYY-MM.",
        )

    return QueryPlan(
        sql=f"""
        SELECT SUBSTR(order_date, 1, 7) AS month,
               region,
               ROUND(SUM(quantity * unit_price * (1 - discount_pct)), 2) AS revenue,
               COUNT(*) AS order_count
        FROM sales_orders
        WHERE {sales_date}
        GROUP BY month, region
        ORDER BY month, revenue DESC
        LIMIT 25
        """,
        confidence=0.55,
        route="fallback_sales_summary",
        rationale="Fallback route: produced a broad sales summary because no specific intent matched.",
    )
