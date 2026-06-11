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
from datatalk.sql_guard import UnsafeSQL, validate_read_only_select


def load_jsonl(path: Path, limit: int = 0) -> list[dict[str, str]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
            if limit and len(records) >= limit:
                break
    return records


def normalize_sql(sql: str) -> str:
    cleaned = " ".join(str(sql).strip().split()).lower()
    cleaned = re.sub(r"\s*([(),=<>+*/-])\s*", r"\1", cleaned)
    return cleaned.rstrip(";")


def generate_batch(model, tokenizer, prompts: list[str], device: str, max_new_tokens: int) -> list[str]:
    encoded = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=1024,
    ).to(device)
    outputs = model.generate(
        **encoded,
        max_new_tokens=max_new_tokens,
        num_beams=4,
        do_sample=False,
    )
    return tokenizer.batch_decode(outputs, skip_special_tokens=True)


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
    parser = argparse.ArgumentParser(description="Evaluate a DataTalk text-to-SQL model.")
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--data-file", default=str(TRAINING_DIR / "domain_text_to_sql_test.jsonl"))
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-new-tokens", type=int, default=180)
    parser.add_argument("--output-report", default=str(REPORTS_DIR / "text_to_sql_eval_report.json"))
    args = parser.parse_args()

    try:
        import torch
        from transformers.utils import logging as transformers_logging
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:
        raise SystemExit("Missing torch/transformers. Install requirements-train.txt first.") from exc

    transformers_logging.set_verbosity_error()
    records = load_jsonl(Path(args.data_file), args.limit)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_dir)
    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    model.to(device)
    model.eval()

    exact = 0
    safe_select = 0
    sqlite_checked = 0
    sqlite_executable = 0
    examples = []

    for batch_index, start in enumerate(range(0, len(records), args.batch_size), start=1):
        batch = records[start : start + args.batch_size]
        predictions = generate_batch(
            model,
            tokenizer,
            [record["input"] for record in batch],
            device,
            args.max_new_tokens,
        )
        for record, prediction in zip(batch, predictions):
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

            if len(examples) < 12 and not is_exact:
                examples.append(
                    {
                        "id": record.get("id"),
                        "source": record.get("source"),
                        "question": record.get("question"),
                        "prediction": prediction,
                        "expected": expected,
                        "safe_select": is_safe,
                        "sqlite_executable": is_sqlite_executable,
                    }
                )
        if batch_index == 1 or batch_index % 25 == 0:
            print(
                json.dumps(
                    {
                        "event": "progress",
                        "records_done": min(start + args.batch_size, len(records)),
                        "records_total": len(records),
                    }
                ),
                flush=True,
            )

    total = max(1, len(records))
    report = {
        "model_dir": args.model_dir,
        "data_file": args.data_file,
        "records": len(records),
        "device": device,
        "exact_match": exact / total,
        "safe_select_rate": safe_select / total,
        "sqlite_executable_rate": sqlite_executable / sqlite_checked if sqlite_checked else None,
        "sqlite_checked_records": sqlite_checked,
        "mismatch_examples": examples,
    }
    Path(args.output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
