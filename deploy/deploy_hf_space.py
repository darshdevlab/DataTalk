#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy DataTalk to a free Hugging Face Docker Space.")
    parser.add_argument("--repo-id", default="DarshDev/DataTalk")
    parser.add_argument("--space-dir", default=str(Path(__file__).resolve().parent / "hf_space"))
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi, create_repo
        from huggingface_hub.utils import HfHubHTTPError, LocalTokenNotFoundError
    except ImportError as exc:
        raise SystemExit(
            "Missing huggingface_hub. Install with:\n"
            "  python3 -m pip install --user huggingface_hub\n"
            "or use the existing training venv:\n"
            "  /Users/darsh/.cache/datatalk-slm-venv/bin/python deploy/deploy_hf_space.py"
        ) from exc

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    api = HfApi(token=token)

    try:
        who = api.whoami(token=token)
    except (HfHubHTTPError, LocalTokenNotFoundError) as exc:
        raise SystemExit(
            "No local Hugging Face write login was found.\n\n"
            "Run one of these, then rerun this script:\n"
            "  huggingface-cli login\n"
            "or:\n"
            "  export HF_TOKEN=hf_your_write_token\n"
        ) from exc

    space_dir = Path(args.space_dir)
    if not space_dir.exists():
        raise SystemExit(f"Space directory not found: {space_dir}")

    create_repo(
        repo_id=args.repo_id,
        repo_type="space",
        space_sdk="docker",
        private=args.private,
        exist_ok=True,
        token=token,
    )
    api.upload_folder(
        folder_path=str(space_dir),
        repo_id=args.repo_id,
        repo_type="space",
        commit_message="Deploy DataTalk API",
        ignore_patterns=["._*", "__pycache__/*", "*.pyc"],
        token=token,
    )

    owner, name = args.repo_id.split("/", 1)
    print(f"Authenticated as: {who.get('name') or who.get('fullname') or who}")
    print(f"Space repo: https://huggingface.co/spaces/{args.repo_id}")
    print(f"App URL: https://{owner.lower()}-{name.lower()}.hf.space")
    print(f"Health URL: https://{owner.lower()}-{name.lower()}.hf.space/health")
    print(f"Query URL: https://{owner.lower()}-{name.lower()}.hf.space/query")


if __name__ == "__main__":
    main()
