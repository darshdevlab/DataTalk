#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatalk.config import DB_PATH
from datatalk.data import init_db, table_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the synthetic DataTalk company database.")
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    db_path = init_db(Path(args.db_path), overwrite=args.overwrite, seed=args.seed)
    print(json.dumps({"db_path": str(db_path), "table_counts": table_counts(db_path)}, indent=2))


if __name__ == "__main__":
    main()
