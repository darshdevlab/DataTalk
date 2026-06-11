#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.intent_compiler import compile_question, detect_intent_slots


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile a DataTalk question into a supported SQL template.")
    parser.add_argument("question")
    args = parser.parse_args()

    slots = detect_intent_slots(args.question)
    plan = compile_question(args.question)
    print(
        json.dumps(
            {
                "question": args.question,
                "slots": asdict(slots),
                "route": plan.route,
                "confidence": plan.confidence,
                "sql": plan.sql,
                "rationale": plan.rationale,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
