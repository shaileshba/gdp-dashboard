"""Loads the processed Parquet files into an in-memory DuckDB database once, at startup.

The history table is small (about 87k rows), so every query runs in memory in a few milliseconds.
"""

from __future__ import annotations

import threading
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

# Ways to group countries. Keys are what the API accepts and the column name in `countries`.
GROUPINGS = {
    "maddison_region": "Maddison region",
    "wb_region": "World Bank region",
    "income_group": "Income group",
}
# Income groups have a natural order (poorest first), so the dashboard can colour them as a ramp.
INCOME_ORDER = ["Low income", "Lower middle income", "Upper middle income", "High income"]
UNCLASSIFIED = "Unclassified"
# Labels that rest on the country's own data (as opposed to growth borrowed from a parent or region).
MEASURED_FLAGS = ("observed", "interpolated", "extended")


class MissingDataError(RuntimeError):
    pass


class Store:
    """Holds one DuckDB connection. Each query gets its own cursor, which is safe across threads."""

    def __init__(self, processed_dir: Path = PROCESSED_DIR):
        missing = [n for n in ("history", "countries") if not (processed_dir / f"{n}.parquet").exists()]
        if missing:
            raise MissingDataError(
                f"Missing {', '.join(missing)}.parquet in {processed_dir}. "
                "Build the data first: cd pipeline; uv run python -m gdp_pipeline"
            )
        self._con = duckdb.connect()
        self._lock = threading.Lock()
        p = processed_dir.as_posix()
        self._con.execute(f"CREATE TABLE history AS SELECT * FROM read_parquet('{p}/history.parquet')")
        self._con.execute(f"""
            CREATE TABLE countries AS
            SELECT iso3, name,
                   coalesce(trim(maddison_region), '{UNCLASSIFIED}') AS maddison_region,
                   coalesce(trim(wb_region), '{UNCLASSIFIED}') AS wb_region,
                   coalesce(trim(income_group), '{UNCLASSIFIED}') AS income_group
            FROM read_parquet('{p}/countries.parquet')
        """)

    def query(self, sql: str, params: list | None = None) -> list[dict]:
        with self._lock:
            cur = self._con.cursor()
        try:
            res = cur.execute(sql, params or [])
            cols = [d[0] for d in res.description]
            return [dict(zip(cols, row, strict=True)) for row in res.fetchall()]
        finally:
            cur.close()
