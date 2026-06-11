from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DATASET_DIR = PROJECT_ROOT / "dataset"
DATA_DIR = ARTIFACTS_DIR / "data"
TRAINING_DIR = ARTIFACTS_DIR / "training"
REPORTS_DIR = ARTIFACTS_DIR / "reports"
MODELS_DIR = ARTIFACTS_DIR / "models"
DB_PATH = DATA_DIR / "company.sqlite"


def ensure_artifact_dirs() -> None:
    for path in (DATASET_DIR, DATA_DIR, TRAINING_DIR, REPORTS_DIR, MODELS_DIR):
        path.mkdir(parents=True, exist_ok=True)
