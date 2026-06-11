#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.config import TRAINING_DIR, ensure_artifact_dirs
from datatalk.lms_schema import lms_schema_context
from datatalk.prompts import build_text_to_sql_prompt
from datatalk.router import route_question


COMPANY_INTENTS = [
    "show revenue by region",
    "list top products by revenue",
    "show top customers by spend",
    "find churn risk tickets",
    "show open support tickets by priority",
    "show employee attrition by department",
    "show overdue invoices",
    "show monthly revenue trend",
]

PERIOD_PHRASES = [
    "for 2025",
    "in 2025",
    "for last year",
    "for 2026",
    "in 2026",
    "for Q1",
    "for quarter 1",
    "for Q2",
    "for Q3",
    "for Q4",
]

TRAIN_LEADS = [
    "",
    "please ",
    "can you ",
    "i need to ",
    "for the dashboard, ",
    "for the finance team, ",
    "create a query to ",
    "build sql to ",
]

VALIDATION_LEADS = [
    "could you ",
    "for my report, ",
    "in the analytics view, ",
    "prepare sql to ",
]

TEST_LEADS = [
    "i want a query that will ",
    "from the data mart, ",
    "for leadership review, ",
    "write sql to ",
]

TAILS = [
    "",
    " sorted clearly",
    " with the largest values first",
    " and limit long detail lists",
    " for the executive dashboard",
    " using the company schema",
]

CONTEXTS = [
    "",
    " for weekly review",
    " for monthly review",
    " for the operations team",
    " for the finance review",
    " for the customer success team",
    " for an executive summary",
    " for a KPI table",
    " for a board update",
    " for the analytics workspace",
    " for the admin dashboard",
    " for a saved report",
]

STYLE_HINTS = [
    "",
    " with clear aliases",
    " with grouped totals",
    " as a read only select",
    " using explicit joins",
    " ordered by the main metric",
    " with stable column names",
    " without extra explanation",
]

LMS_TEMPLATES = [
    (
        "show active learners by organization",
        """
        SELECT o.organization_name, COUNT(*) AS active_learners
        FROM core.users u
        JOIN core.organizations o ON o.organization_id = u.organization_id
        WHERE u.status = 'active' AND u.role = 'learner'
        GROUP BY o.organization_id, o.organization_name
        ORDER BY active_learners DESC
        """,
    ),
    (
        "show courses with the highest completion rate",
        """
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
    ),
    (
        "find at risk learners in the last 30 days",
        """
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
    ),
    (
        "show overdue invoices by organization",
        """
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
    ),
    (
        "show organizations with churn risk",
        """
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
    ),
    (
        "show course engagement by device type",
        """
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
    ),
    (
        "show average assessment score by course category",
        """
        SELECT c.category,
               ROUND(AVG(a.score_pct), 2) AS avg_score_pct,
               COUNT(*) AS assessment_count
        FROM lms.assessments a
        JOIN lms.enrollments e ON e.enrollment_id = a.enrollment_id
        JOIN lms.courses c ON c.course_id = e.course_id
        GROUP BY c.category
        ORDER BY avg_score_pct DESC
        """,
    ),
    (
        "list inactive users who still have enrollments in progress",
        """
        SELECT u.user_id, u.full_name, u.email, COUNT(*) AS open_enrollments
        FROM core.users u
        JOIN lms.enrollments e ON e.user_id = u.user_id
        WHERE u.status != 'active'
          AND e.status IN ('in_progress', 'not_started')
        GROUP BY u.user_id, u.full_name, u.email
        ORDER BY open_enrollments DESC
        LIMIT 25
        """,
    ),
]


def normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().split())


def lms_prompt(question: str) -> str:
    return (
        "You are DataTalk-SQL, a small model specialized for a company LMS database.\n"
        f"{lms_schema_context()}\n\n"
        f"Question: {question.strip()}\n"
        "SQL:"
    )


def make_company_question(rng: random.Random, split: str) -> tuple[str, str, str]:
    leads = {"train": TRAIN_LEADS, "validation": VALIDATION_LEADS, "test": TEST_LEADS}[split]
    intent = rng.choice(COMPANY_INTENTS)
    period = rng.choice(PERIOD_PHRASES)
    tail = rng.choice(TAILS)
    context = rng.choice(CONTEXTS)
    style = rng.choice(STYLE_HINTS)
    question = f"{rng.choice(leads)}{intent} {period}{tail}{context}{style}".strip()
    sql = normalize_sql(route_question(question).sql)
    return question, build_text_to_sql_prompt(question), sql


def make_lms_question(rng: random.Random, split: str) -> tuple[str, str, str]:
    leads = {"train": TRAIN_LEADS, "validation": VALIDATION_LEADS, "test": TEST_LEADS}[split]
    question_base, sql = rng.choice(LMS_TEMPLATES)
    tail = rng.choice(TAILS)
    context = rng.choice(CONTEXTS)
    style = rng.choice(STYLE_HINTS)
    question = f"{rng.choice(leads)}{question_base}{tail}{context}{style}".strip()
    return question, lms_prompt(question), normalize_sql(sql)


def build_records(split: str, count: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    records: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    attempts = 0
    while len(records) < count:
        attempts += 1
        if attempts > count * 200:
            raise RuntimeError(f"Could not generate {count} unique {split} records.")
        if rng.random() < 0.5:
            source = "datatalk_company"
            question, prompt, sql = make_company_question(rng, split)
        else:
            source = "company_lms_schema"
            question, prompt, sql = make_lms_question(rng, split)
        key = (prompt, sql)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "id": f"domain-{split}-{len(records) + 1:05d}",
                "source": source,
                "split": split,
                "question": question,
                "input": prompt,
                "output": sql,
            }
        )
    rng.shuffle(records)
    return records


def write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DataTalk domain-only text-to-SQL splits.")
    parser.add_argument("--train-count", type=int, default=6000)
    parser.add_argument("--validation-count", type=int, default=750)
    parser.add_argument("--test-count", type=int, default=750)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--output-train", default=str(TRAINING_DIR / "domain_text_to_sql_train.jsonl"))
    parser.add_argument("--output-validation", default=str(TRAINING_DIR / "domain_text_to_sql_validation.jsonl"))
    parser.add_argument("--output-test", default=str(TRAINING_DIR / "domain_text_to_sql_test.jsonl"))
    args = parser.parse_args()

    ensure_artifact_dirs()
    train_records = build_records("train", args.train_count, args.seed)
    validation_records = build_records("validation", args.validation_count, args.seed + 1)
    test_records = build_records("test", args.test_count, args.seed + 2)

    write_jsonl(Path(args.output_train), train_records)
    write_jsonl(Path(args.output_validation), validation_records)
    write_jsonl(Path(args.output_test), test_records)

    summary = {
        "train_path": args.output_train,
        "validation_path": args.output_validation,
        "test_path": args.output_test,
        "train_records": len(train_records),
        "validation_records": len(validation_records),
        "test_records": len(test_records),
        "sources": {
            split: {
                source: sum(1 for record in records if record["source"] == source)
                for source in ("datatalk_company", "company_lms_schema")
            }
            for split, records in (
                ("train", train_records),
                ("validation", validation_records),
                ("test", test_records),
            )
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
