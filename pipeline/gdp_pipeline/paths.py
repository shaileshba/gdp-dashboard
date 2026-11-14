"""Folder locations used by the pipeline. Everything lives under the repo's data/ folder."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # files exactly as downloaded (never edited by hand)
PROCESSED_DIR = DATA_DIR / "processed"  # cleaned outputs the model and API read
DOCS_DIR = REPO_ROOT / "docs"

for _d in (RAW_DIR, PROCESSED_DIR, DOCS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
