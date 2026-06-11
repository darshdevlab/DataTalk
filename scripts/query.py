#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.config import DB_PATH
from datatalk.executor import answer_question
from datatalk.model_sql import generate_sql_with_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask DataTalk a natural-language company-data question.")
    parser.add_argument("question")
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--model-dir", default="", help="Optional fine-tuned SLM directory.")
    parser.add_argument("--mode", choices=["compiler", "router"], default="compiler")
    args = parser.parse_args()

    sql = None
    if args.model_dir:
        sql = generate_sql_with_model(args.question, Path(args.model_dir))
    response = answer_question(args.question, db_path=Path(args.db_path), sql=sql, mode=args.mode)
    print(json.dumps(asdict(response), indent=2))


if __name__ == "__main__":
    main()
