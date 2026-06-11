from __future__ import annotations

from dataclasses import dataclass

from .router import QueryPlan, route_question as route_company_question


@dataclass(frozen=True)
class IntentSlots:
    intent: str
    family: str
    period: str | None = None


COMPANY_INTENTS = {
    "revenue_by_region",
    "top_products",
    "customer_revenue",
    "churn_risk_tickets",
    "tickets_by_status_priority",
    "attrition_by_department",
    "overdue_invoices",
    "monthly_revenue_trend",
}

LMS_SQL = {
    "lms_active_learners_by_org": """
        SELECT o.organization_name, COUNT(*) AS active_learners
        FROM core.users u
        JOIN core.organizations o ON o.organization_id = u.organization_id
        WHERE u.status = 'active' AND u.role = 'learner'
        GROUP BY o.organization_id, o.organization_name
        ORDER BY active_learners DESC
    """,
    "lms_course_completion_rate": """
        SELECT c.title,
               ROUND(SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS completion_rate,
               COUNT(*) AS enrollment_count
        FROM lms.enrollments e
        JOIN lms.courses c ON c.course_id = e.course_id
        GROUP BY c.course_id, c.title
        HAVING COUNT(*) >= 10
        ORDER BY completion_rate DESC
        LIMIT 10
    """,
    "lms_at_risk_learners": """
        SELECT u.full_name, u.email, c.title, e.progress_pct, e.enrolled_at
        FROM lms.enrollments e
        JOIN core.users u ON u.user_id = e.user_id
        JOIN lms.courses c ON c.course_id = e.course_id
        WHERE e.status != 'completed'
          AND e.progress_pct < 35
          AND e.enrolled_at >= CURRENT_DATE - INTERVAL '30 days'
        ORDER BY e.progress_pct ASC, e.enrolled_at ASC
        LIMIT 25
    """,
    "lms_overdue_invoices_by_org": """
        SELECT o.organization_name,
               COUNT(*) AS overdue_invoice_count,
               ROUND(SUM(i.amount_usd), 2) AS overdue_amount_usd
        FROM billing.invoices i
        JOIN core.organizations o ON o.organization_id = i.organization_id
        WHERE i.status = 'open'
          AND i.due_date < CURRENT_DATE
        GROUP BY o.organization_id, o.organization_name
        ORDER BY overdue_amount_usd DESC
    """,
    "lms_churn_risk_orgs": """
        SELECT o.organization_name,
               COUNT(DISTINCT t.ticket_id) AS risky_ticket_count,
               COUNT(DISTINCT i.invoice_id) AS overdue_invoice_count,
               MIN(t.sentiment_score) AS worst_sentiment
        FROM core.organizations o
        LEFT JOIN support.tickets t ON t.organization_id = o.organization_id
          AND t.status != 'closed'
          AND (t.priority IN ('high', 'critical') OR t.sentiment_score <= 2)
        LEFT JOIN billing.invoices i ON i.organization_id = o.organization_id
          AND i.status = 'open'
          AND i.due_date < CURRENT_DATE
        GROUP BY o.organization_id, o.organization_name
        HAVING COUNT(DISTINCT t.ticket_id) > 0 OR COUNT(DISTINCT i.invoice_id) > 0
        ORDER BY risky_ticket_count DESC, overdue_invoice_count DESC
        LIMIT 20
    """,
    "lms_course_engagement_by_device": """
        SELECT c.title,
               e.device_type,
               COUNT(*) AS event_count,
               COUNT(DISTINCT e.user_id) AS unique_users
        FROM analytics.events e
        JOIN lms.courses c ON c.course_id = e.course_id
        WHERE e.event_at >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY c.course_id, c.title, e.device_type
        ORDER BY event_count DESC
        LIMIT 30
    """,
    "lms_avg_assessment_by_category": """
        SELECT c.category,
               ROUND(AVG(a.score_pct), 2) AS avg_score_pct,
               COUNT(*) AS assessment_count
        FROM lms.assessments a
        JOIN lms.enrollments e ON e.enrollment_id = a.enrollment_id
        JOIN lms.courses c ON c.course_id = e.course_id
        GROUP BY c.category
        ORDER BY avg_score_pct DESC
    """,
    "lms_inactive_users_open_enrollments": """
        SELECT u.user_id, u.full_name, u.email, COUNT(*) AS open_enrollments
        FROM core.users u
        JOIN lms.enrollments e ON e.user_id = u.user_id
        WHERE u.status != 'active'
          AND e.status IN ('in_progress', 'not_started')
        GROUP BY u.user_id, u.full_name, u.email
        ORDER BY open_enrollments DESC
        LIMIT 25
    """,
}


def normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().split())


def detect_company_intent(question: str) -> str:
    q = question.lower()
    if "revenue" in q and "region" in q:
        return "revenue_by_region"
    if ("top product" in q or "top products" in q or "best product" in q or "best products" in q) and "revenue" in q:
        return "top_products"
    if "top customer" in q or "top customers" in q or ("customer" in q and ("spend" in q or "sales" in q or "revenue" in q)):
        return "customer_revenue"
    if "churn" in q and "ticket" in q:
        return "churn_risk_tickets"
    if "support ticket" in q or ("ticket" in q and ("priority" in q or "open" in q or "status" in q)):
        return "tickets_by_status_priority"
    if "attrition" in q or ("employee" in q and ("left" in q or "turnover" in q)):
        return "attrition_by_department"
    if "overdue invoice" in q or ("invoice" in q and "open" in q):
        return "overdue_invoices"
    if "monthly" in q or "trend" in q:
        return "monthly_revenue_trend"
    return "fallback_sales_summary"


def detect_lms_intent(question: str) -> str | None:
    q = question.lower()
    if "active learner" in q and "organization" in q:
        return "lms_active_learners_by_org"
    if "completion rate" in q or ("highest completion" in q and "course" in q):
        return "lms_course_completion_rate"
    if "at risk learner" in q or "at-risk learner" in q:
        return "lms_at_risk_learners"
    if "overdue invoice" in q and "organization" in q:
        return "lms_overdue_invoices_by_org"
    if "organization" in q and "churn risk" in q:
        return "lms_churn_risk_orgs"
    if "course engagement" in q and "device" in q:
        return "lms_course_engagement_by_device"
    if "assessment score" in q or "course category" in q:
        return "lms_avg_assessment_by_category"
    if "inactive user" in q and "enrollment" in q:
        return "lms_inactive_users_open_enrollments"
    return None


def detect_period(question: str) -> str:
    q = question.lower()
    if "q1" in q or "quarter 1" in q:
        return "q1"
    if "q2" in q:
        return "q2"
    if "q3" in q:
        return "q3"
    if "q4" in q:
        return "q4"
    if "2026" in q:
        return "2026"
    if "2025" in q or "last year" in q:
        return "2025"
    return "default"


def detect_intent_slots(question: str) -> IntentSlots:
    lms_intent = detect_lms_intent(question)
    if lms_intent:
        return IntentSlots(intent=lms_intent, family="lms")

    company_intent = detect_company_intent(question)
    return IntentSlots(intent=company_intent, family="company", period=detect_period(question))


def company_seed_question(slots: IntentSlots) -> str:
    period = {
        "q1": "for Q1",
        "q2": "for Q2",
        "q3": "for Q3",
        "q4": "for Q4",
        "2026": "for 2026",
        "2025": "for 2025",
        "default": "",
        None: "",
    }[slots.period]
    base = {
        "revenue_by_region": "show revenue by region",
        "top_products": "show top products by revenue",
        "customer_revenue": "show top customers by spend",
        "churn_risk_tickets": "find churn risk tickets",
        "tickets_by_status_priority": "show open support tickets by priority",
        "attrition_by_department": "show employee attrition by department",
        "overdue_invoices": "show overdue invoices",
        "monthly_revenue_trend": "show monthly revenue trend",
        "fallback_sales_summary": "show sales summary",
    }[slots.intent]
    return f"{base} {period}".strip()


def compile_intent_slots(slots: IntentSlots) -> QueryPlan:
    if slots.family == "lms":
        sql = LMS_SQL[slots.intent]
        return QueryPlan(
            sql=normalize_sql(sql),
            confidence=0.96,
            route=slots.intent,
            rationale="Matched a supported LMS intent and compiled schema-qualified SQL.",
        )

    plan = route_company_question(company_seed_question(slots))
    return QueryPlan(
        sql=normalize_sql(plan.sql),
        confidence=0.96 if slots.intent in COMPANY_INTENTS else 0.72,
        route=slots.intent,
        rationale="Matched a supported company intent/slot pattern and compiled SQLite SQL.",
    )


def compile_question(question: str) -> QueryPlan:
    return compile_intent_slots(detect_intent_slots(question))
