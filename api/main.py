"""HTTP endpoints for the history dashboard.

Run it with:  uv run python -m api        (then open http://127.0.0.1:8000)

When app/dist exists (after `npm run build` in app/), the dashboard itself is served from "/",
so one command runs everything. During frontend development, `npm run dev` proxies /api here.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles

from .data import GROUPINGS, INCOME_ORDER, MEASURED_FLAGS, REPO_ROOT, Store

DIST_DIR = REPO_ROOT / "app" / "dist"
MAX_SERIES = 12
_MEASURED = ", ".join(f"'{f}'" for f in MEASURED_FLAGS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "store", None) is None:  # tests inject their own store
        app.state.store = Store()
    yield


app = FastAPI(title="World GDP Dashboard API", lifespan=lifespan)


def _store(request: Request) -> Store:
    return request.app.state.store


def _year_range(store: Store) -> tuple[int, int]:
    row = store.query("SELECT min(year) AS lo, max(year) AS hi FROM history")[0]
    return int(row["lo"]), int(row["hi"])


@app.get("/api/meta")
def meta(request: Request):
    """Year range, the country list with its groups, and the groups in each grouping."""
    store = _store(request)
    lo, hi = _year_range(store)
    countries = store.query("SELECT * FROM countries ORDER BY name")
    groupings = []
    for key, label in GROUPINGS.items():
        names = sorted({c[key] for c in countries})
        if key == "income_group":
            names = [g for g in INCOME_ORDER if g in names] + [g for g in names if g not in INCOME_ORDER]
        groupings.append({"key": key, "label": label, "groups": names})
    return {
        "first_year": lo,
        "last_year": hi,
        "measured_flags": list(MEASURED_FLAGS),
        "groupings": groupings,
        "countries": countries,
    }


@app.get("/api/snapshot")
def snapshot(request: Request, year: int):
    """Every country in one year, with ranks, share of world GDP and 10-year growth of GDP per person."""
    store = _store(request)
    lo, hi = _year_range(store)
    if not lo <= year <= hi:
        raise HTTPException(400, f"year must be between {lo} and {hi}")
    span = year - max(lo, year - 10)
    return store.query(
        """
        WITH now AS (SELECT * FROM history WHERE year = ?),
             past AS (SELECT iso3, gdppc AS gdppc_past FROM history WHERE year = ?)
        SELECT now.iso3, c.name, now.year, now.gdp, now.gdppc, now.pop,
               now.flag, now.gdppc_flag, now.pop_flag,
               now.gdp / sum(now.gdp) OVER () AS world_share,
               CASE WHEN ? > 0 THEN power(now.gdppc / past.gdppc_past, 1.0 / ?) - 1 END AS gdppc_growth_10y,
               rank() OVER (ORDER BY now.gdp DESC) AS rank_gdp,
               rank() OVER (ORDER BY now.gdppc DESC) AS rank_gdppc,
               rank() OVER (ORDER BY now.pop DESC) AS rank_pop
        FROM now JOIN countries c USING (iso3) LEFT JOIN past USING (iso3)
        ORDER BY now.gdp DESC
        """,
        [year, year - span, span, max(span, 1)],
    )


@app.get("/api/series")
def series(request: Request, iso3: str = Query(..., description="Comma-separated ISO3 codes")):
    """Full yearly history for up to 12 countries, keyed by ISO3 code."""
    codes = list(dict.fromkeys(c.strip().upper() for c in iso3.split(",") if c.strip()))
    if not codes:
        raise HTTPException(400, "give at least one ISO3 code")
    if len(codes) > MAX_SERIES:
        raise HTTPException(400, f"at most {MAX_SERIES} countries at once")
    rows = _store(request).query(
        "SELECT iso3, year, gdp, gdppc, pop, flag FROM history WHERE list_contains(?, iso3) ORDER BY iso3, year",
        [codes],
    )
    out: dict[str, list] = {c: [] for c in codes}
    for r in rows:
        out[r.pop("iso3")].append(r)
    unknown = [c for c, v in out.items() if not v]
    if unknown:
        raise HTTPException(404, f"unknown country code(s): {', '.join(unknown)}")
    return out


@app.get("/api/world")
def world(request: Request):
    """World totals per year, and the share of world GDP that rests on countries' own data."""
    return _store(request).query(f"""
        SELECT year, sum(gdp) AS gdp, sum(pop) AS pop, sum(gdp) / sum(pop) AS gdppc,
               coalesce(sum(gdp) FILTER (WHERE flag IN ({_MEASURED})), 0) / sum(gdp) AS measured_share,
               count(*) FILTER (WHERE gdppc_flag = 'observed') AS countries_observed
        FROM history GROUP BY year ORDER BY year
    """)


@app.get("/api/groups")
def groups(request: Request, by: str = "maddison_region"):
    """GDP and population per group per year (for the share-of-world chart)."""
    if by not in GROUPINGS:
        raise HTTPException(400, f"by must be one of: {', '.join(GROUPINGS)}")
    # `by` was checked against a fixed list above, so it is safe to put in the SQL.
    return _store(request).query(f"""
        SELECT h.year, c.{by} AS grp, sum(h.gdp) AS gdp, sum(h.pop) AS pop
        FROM history h JOIN countries c USING (iso3)
        GROUP BY ALL ORDER BY h.year, grp
    """)


if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="dashboard")
else:
    @app.get("/")
    def no_frontend():
        return {"message": "The API is running, but the dashboard is not built yet. "
                           "Build it with: cd app; npm install; npm run build", "docs": "/docs"}
