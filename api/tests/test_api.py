"""API tests on a tiny made-up dataset, so they run without downloading anything."""

from __future__ import annotations

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.data import Store
from api.main import app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("processed")
    con = duckdb.connect()
    # Two countries, 2000-2020. AAA doubles GDP per person over 20 years; BBB is flat.
    con.execute(f"""
        COPY (
            SELECT iso3, year::BIGINT AS year, gdppc, pop, gdppc * pop AS gdp,
                   flag AS gdppc_flag, 'observed' AS pop_flag, flag
            FROM (
                SELECT 'AAA' AS iso3, y AS year, 1000 * power(2, (y - 2000) / 20.0) AS gdppc, 1e6 AS pop,
                       'observed' AS flag FROM range(2000, 2021) t(y)
                UNION ALL
                SELECT 'BBB', y, 500.0, 3e6, CASE WHEN y < 2010 THEN 'regional' ELSE 'observed' END
                FROM range(2000, 2021) t(y)
            )
        ) TO '{(d / "history.parquet").as_posix()}' (FORMAT parquet)
    """)
    con.execute(f"""
        COPY (SELECT * FROM (VALUES
            ('AAA', 'Aland', 'Western Europe', 'Europe & Central Asia ', 'High income', NULL),
            ('BBB', 'Bland', 'Latin America', NULL, NULL, NULL)
        ) t(iso3, name, maddison_region, wb_region, income_group, former_state))
        TO '{(d / "countries.parquet").as_posix()}' (FORMAT parquet)
    """)
    app.state.store = Store(d)
    with TestClient(app) as c:
        yield c
    app.state.store = None


def test_meta(client):
    m = client.get("/api/meta").json()
    assert (m["first_year"], m["last_year"]) == (2000, 2020)
    wb = next(g for g in m["groupings"] if g["key"] == "wb_region")
    assert wb["groups"] == ["Europe & Central Asia", "Unclassified"]  # trimmed, nulls labelled
    income = next(g for g in m["groupings"] if g["key"] == "income_group")
    assert income["groups"] == ["High income", "Unclassified"]


def test_snapshot_shares_ranks_and_growth(client):
    rows = client.get("/api/snapshot", params={"year": 2020}).json()
    by = {r["iso3"]: r for r in rows}
    assert sum(r["world_share"] for r in rows) == pytest.approx(1.0)
    # AAA GDP = 2000 * 1e6 = 2e9, BBB = 1.5e9
    assert by["AAA"]["rank_gdp"] == 1 and by["BBB"]["rank_pop"] == 1
    assert by["AAA"]["gdppc_growth_10y"] == pytest.approx(2 ** (1 / 20) - 1)  # doubles in 20 years
    assert by["BBB"]["gdppc_growth_10y"] == pytest.approx(0.0)


def test_snapshot_first_year_has_no_growth(client):
    rows = client.get("/api/snapshot", params={"year": 2000}).json()
    assert all(r["gdppc_growth_10y"] is None for r in rows)


def test_snapshot_rejects_out_of_range_year(client):
    assert client.get("/api/snapshot", params={"year": 1900}).status_code == 400


def test_series(client):
    s = client.get("/api/series", params={"iso3": "aaa, BBB"}).json()
    assert list(s) == ["AAA", "BBB"]
    assert len(s["AAA"]) == 21 and s["AAA"][0]["year"] == 2000
    assert client.get("/api/series", params={"iso3": "ZZZ"}).status_code == 404


def test_world_measured_share(client):
    w = {r["year"]: r for r in client.get("/api/world").json()}
    # In 2000, BBB (GDP 1.5e9) is regional and AAA (1e9) is observed.
    assert w[2000]["measured_share"] == pytest.approx(1e9 / 2.5e9)
    assert w[2020]["measured_share"] == pytest.approx(1.0)
    assert w[2000]["pop"] == pytest.approx(4e6)


def test_groups(client):
    rows = client.get("/api/groups", params={"by": "income_group"}).json()
    assert {r["grp"] for r in rows} == {"High income", "Unclassified"}
    assert client.get("/api/groups", params={"by": "name; DROP TABLE history"}).status_code == 400
