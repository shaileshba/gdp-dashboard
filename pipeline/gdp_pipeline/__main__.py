"""Command line:  uv run python -m gdp_pipeline [fetch|build|all] [--force]

  fetch   download raw data into data/raw (skips files already there unless --force)
  build   create data/processed/*.parquet and docs/data_quality_report.md
  all     fetch, then build (default)
"""

import argparse

from .build import build_history, write_parquet
from .report import write_report
from .sources import fetch_all


def main() -> None:
    ap = argparse.ArgumentParser(prog="gdp_pipeline")
    ap.add_argument("step", nargs="?", default="all", choices=["fetch", "build", "all"])
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = ap.parse_args()

    if args.step in ("fetch", "all"):
        print("Fetching sources")
        fetch_all(force=args.force)
    if args.step in ("build", "all"):
        print("Building history")
        tables = build_history()
        write_parquet(tables)
        print(f"  report: {write_report(tables)}")


if __name__ == "__main__":
    main()
