#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.config import DB_PATH, REPORTS_DIR, ensure_artifact_dirs
from datatalk.executor import answer_question
from datatalk.model_sql import generate_sql_with_model
from datatalk.sql_guard import UnsafeSQL


BENCHMARK_QUESTIONS = [
    "Show revenue by region for 2025",
    "Top products by revenue for Q1",
    "Top customers by spend for 2026",
    "Find churn risk tickets for Q4",
    "Show open support tickets by priority for Q1",
    "Employee attrition by department",
    "Show overdue invoices",
    "Monthly revenue trend for 2025",
]


def run_once(question: str, db_path: Path, model_dir: Path | None) -> dict:
    started = time.perf_counter()
    generated_sql = None
    mode = "reference_router"
    if model_dir:
        mode = "trained_slm"
        generated_sql = generate_sql_with_model(question, model_dir)
    response = answer_question(question, db_path=db_path, sql=generated_sql)
    return {
        "question": question,
        "mode": mode,
        "latency_ms": (time.perf_counter() - started) * 1000,
        "executor_latency_ms": response.latency_ms,
        "route": response.route,
        "row_count": len(response.rows),
        "sql": response.sql,
        "answer": response.answer,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark DataTalk query latency and SQL validity.")
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--model-dir", default="", help="Optional fine-tuned SLM directory.")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--output", default=str(REPORTS_DIR / "benchmark.json"))
    args = parser.parse_args()

    ensure_artifact_dirs()
    model_dir = Path(args.model_dir) if args.model_dir else None
    all_runs = []
    failures = []
    for _ in range(args.iterations):
        for question in BENCHMARK_QUESTIONS:
            try:
                all_runs.append(run_once(question, Path(args.db_path), model_dir))
            except (RuntimeError, UnsafeSQL, ValueError) as exc:
                failures.append({"question": question, "error": str(exc)})

    latencies = [row["latency_ms"] for row in all_runs]
    summary = {
        "mode": "trained_slm" if model_dir else "reference_router",
        "questions": len(BENCHMARK_QUESTIONS),
        "iterations": args.iterations,
        "successes": len(all_runs),
        "failures": failures,
        "avg_latency_ms": statistics.mean(latencies) if latencies else None,
        "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else None),
        "runs": all_runs,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "runs"}, indent=2))
    print(f"Saved detailed report: {output}")


if __name__ == "__main__":
    main()
