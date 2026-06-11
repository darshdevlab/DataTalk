#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.config import DATASET_DIR, TRAINING_DIR, ensure_artifact_dirs
from datatalk.lms_schema import lms_schema_context
from datatalk.prompts import build_text_to_sql_prompt
from datatalk.router import route_question


SPIDER_PROMPT = """You are DataTalk-SQL, a small text-to-SQL model.
Return exactly one SQL query. Do not explain.

Database id: {db_id}
Question: {question}
SQL:"""

COMPANY_LMS_TEMPLATES = [
    (
        "Show active learners by organization",
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
        "Which courses have the highest completion rate?",
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
        "Find at risk learners in the last 30 days",
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
        "Show overdue invoices by organization",
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
        "Which organizations have churn risk?",
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
        "Show course engagement by device type",
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
        "Average assessment score by course category",
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
        "List inactive users who still have enrollments in progress",
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

QUESTION_VARIANTS = [
    "{question}",
    "Please {question_lc}",
    "Can you {question_lc}?",
    "I need to {question_lc}",
    "For the LMS dashboard, {question_lc}",
]


def normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().split())


def read_spider_parquet(path: Path, limit: int) -> list[dict]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("Missing pyarrow. Install with: pip install -r requirements-train.txt") from exc

    table = pq.read_table(path)
    rows = table.to_pylist()
    if limit > 0:
        rows = rows[:limit]
    return rows


def build_spider_records(split: str, source_path: Path, limit: int) -> list[dict[str, str]]:
    records = []
    for i, row in enumerate(read_spider_parquet(source_path, limit), start=1):
        question = row["question"].strip()
        records.append(
            {
                "id": f"spider-{split}-{i:05d}",
                "source": "spider",
                "split": split,
                "question": question,
                "input": SPIDER_PROMPT.format(db_id=row["db_id"], question=question),
                "output": normalize_sql(row["query"]),
            }
        )
    return records


def build_company_reference_records(count: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    public_questions = [
        "Show revenue by region for 2025",
        "Top products by revenue for Q1",
        "Top customers by spend for 2026",
        "Find churn risk tickets for Q4",
        "Show open support tickets by priority for Q1",
        "Employee attrition by department",
        "Show overdue invoices",
        "Monthly revenue trend for 2025",
    ]
    records = []
    for i in range(count):
        question = rng.choice(public_questions)
        plan = route_question(question)
        records.append(
            {
                "id": f"company-reference-{i + 1:05d}",
                "source": "datatalk_company",
                "split": "train",
                "question": question,
                "input": build_text_to_sql_prompt(question),
                "output": normalize_sql(plan.sql),
            }
        )
    return records


def build_lms_records(count: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    schema = lms_schema_context()
    records = []
    for i in range(count):
        question, sql = rng.choice(COMPANY_LMS_TEMPLATES)
        variant = rng.choice(QUESTION_VARIANTS).format(question=question, question_lc=question[:1].lower() + question[1:])
        prompt = (
            "You are DataTalk-SQL, a small model specialized for a company LMS database.\n"
            f"{schema}\n\n"
            f"Question: {variant}\n"
            "SQL:"
        )
        records.append(
            {
                "id": f"company-lms-{i + 1:05d}",
                "source": "company_lms_schema",
                "split": "train",
                "question": variant,
                "input": prompt,
                "output": normalize_sql(sql),
            }
        )
    return records


def write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build mixed public + company text-to-SQL training corpus.")
    parser.add_argument("--spider-dir", default=str(DATASET_DIR / "spider_hf"))
    parser.add_argument("--train-spider-limit", type=int, default=7000)
    parser.add_argument("--validation-spider-limit", type=int, default=1034)
    parser.add_argument("--company-reference-count", type=int, default=500)
    parser.add_argument("--company-lms-count", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=21)
    parser.add_argument("--output-train", default=str(TRAINING_DIR / "mixed_text_to_sql_train.jsonl"))
    parser.add_argument("--output-validation", default=str(TRAINING_DIR / "mixed_text_to_sql_validation.jsonl"))
    args = parser.parse_args()

    ensure_artifact_dirs()
    spider_dir = Path(args.spider_dir)
    spider_train = build_spider_records("train", spider_dir / "train.parquet", args.train_spider_limit)
    spider_validation = build_spider_records("validation", spider_dir / "validation.parquet", args.validation_spider_limit)
    company_reference = build_company_reference_records(args.company_reference_count, args.seed)
    company_lms = build_lms_records(args.company_lms_count, args.seed)

    rng = random.Random(args.seed)
    train_records = spider_train + company_reference + company_lms
    rng.shuffle(train_records)
    validation_records = spider_validation + build_lms_records(max(80, args.company_lms_count // 10), args.seed + 1)
    rng.shuffle(validation_records)

    write_jsonl(Path(args.output_train), train_records)
    write_jsonl(Path(args.output_validation), validation_records)

    summary = {
        "train_path": args.output_train,
        "validation_path": args.output_validation,
        "train_records": len(train_records),
        "validation_records": len(validation_records),
        "sources": {
            "spider_train": len(spider_train),
            "spider_validation": len(spider_validation),
            "company_reference": len(company_reference),
            "company_lms_train": len(company_lms),
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
