#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.config import TRAINING_DIR, ensure_artifact_dirs
from datatalk.prompts import build_text_to_sql_prompt
from datatalk.router import route_question


QUESTION_FAMILIES = [
    "Show revenue by region for {period}",
    "Which region had the most revenue in {period}?",
    "Top products by revenue for {period}",
    "Which products sold best during {period}?",
    "Top customers by spend for {period}",
    "Which customers generated the highest sales in {period}?",
    "Find churn risk tickets for {period}",
    "Which customers have high risk support tickets in {period}?",
    "Show open support tickets by priority for {period}",
    "Ticket count by status and priority for {period}",
    "Employee attrition by department",
    "Which department had the most employees leave?",
    "Show overdue invoices",
    "Which customers have the largest overdue invoice amount?",
    "Monthly revenue trend for {period}",
    "Show sales trend by month for {period}",
]

PERIODS = ["2025", "2026", "Q1", "Q2", "Q3", "Q4", "last year"]


def build_examples(count: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    records = []
    for i in range(count):
        template = rng.choice(QUESTION_FAMILIES)
        question = template.format(period=rng.choice(PERIODS))
        if rng.random() < 0.2:
            question = question.replace("Show", "Please show").replace("Which", "Tell me which")
        plan = route_question(question)
        records.append(
            {
                "id": f"datatalk-sql-{i + 1:05d}",
                "question": question,
                "input": build_text_to_sql_prompt(question),
                "output": plan.sql.strip(),
                "route": plan.route,
                "confidence": f"{plan.confidence:.2f}",
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DataTalk text-to-SQL fine-tuning JSONL.")
    parser.add_argument("--count", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--output", default=str(TRAINING_DIR / "text_to_sql.jsonl"))
    args = parser.parse_args()

    ensure_artifact_dirs()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = build_examples(args.count, args.seed)
    with output.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    print(json.dumps({"output": str(output), "records": len(records)}, indent=2))


if __name__ == "__main__":
    main()
