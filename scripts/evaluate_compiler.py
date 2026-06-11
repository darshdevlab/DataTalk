#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.config import DB_PATH, REPORTS_DIR, TRAINING_DIR
from datatalk.intent_compiler import compile_question
from datatalk.sql_guard import UnsafeSQL, validate_read_only_select


def load_jsonl(path: Path) -> list[dict[str, str]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def normalize_sql(sql: str) -> str:
    cleaned = " ".join(str(sql).strip().split()).lower()
    cleaned = re.sub(r"\s*([(),=<>+*/-])\s*", r"\1", cleaned)
    return cleaned.rstrip(";")


def can_execute_sqlite(db_path: Path, sql: str) -> bool:
    try:
        cleaned = validate_read_only_select(sql)
    except UnsafeSQL:
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(f"SELECT * FROM ({cleaned}) LIMIT 1").fetchall()
        return True
    except sqlite3.Error:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic DataTalk intent/slot compiler.")
    parser.add_argument("--data-file", default=str(TRAINING_DIR / "domain_text_to_sql_test.jsonl"))
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--output-report", default=str(REPORTS_DIR / "compiler_eval_report.json"))
    args = parser.parse_args()

    records = load_jsonl(Path(args.data_file))
    exact = 0
    safe_select = 0
    sqlite_checked = 0
    sqlite_executable = 0
    mismatches = []

    for record in records:
        plan = compile_question(record["question"])
        prediction = plan.sql
        expected = record["output"]
        is_exact = normalize_sql(prediction) == normalize_sql(expected)
        exact += int(is_exact)
        try:
            validate_read_only_select(prediction)
            is_safe = True
        except UnsafeSQL:
            is_safe = False
        safe_select += int(is_safe)

        is_sqlite_executable = None
        if record.get("source") == "datatalk_company":
            sqlite_checked += 1
            is_sqlite_executable = can_execute_sqlite(Path(args.db_path), prediction)
            sqlite_executable += int(is_sqlite_executable)

        if len(mismatches) < 20 and not is_exact:
            mismatches.append(
                {
                    "id": record.get("id"),
                    "source": record.get("source"),
                    "question": record.get("question"),
                    "route": plan.route,
                    "prediction": prediction,
                    "expected": expected,
                    "safe_select": is_safe,
                    "sqlite_executable": is_sqlite_executable,
                }
            )

    total = max(1, len(records))
    report = {
        "data_file": args.data_file,
        "records": len(records),
        "exact_match": exact / total,
        "safe_select_rate": safe_select / total,
        "sqlite_executable_rate": sqlite_executable / sqlite_checked if sqlite_checked else None,
        "sqlite_checked_records": sqlite_checked,
        "mismatch_examples": mismatches,
    }
    output_path = Path(args.output_report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
