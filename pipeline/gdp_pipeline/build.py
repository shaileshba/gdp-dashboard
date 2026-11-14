"""Build the joined country-year history from 1500 to the latest year with data.

Output files (data/processed/*.parquet):
  history         iso3, year, gdppc, pop, gdp, and a quality flag for each value
  countries       one row per country: names, Maddison region, World Bank region, income group
  former_states   USSR / Czechoslovakia / Yugoslavia totals (reference only, not in history)
  population_un   UN population, fertility, life expectancy etc., 1950-2100 (model input)
  pwt             Penn World Table growth inputs, 1950-2023 (model calibration)
  world_benchmarks  Maddison's published world totals, for checking our sums
"""

from __future__ import annotations

import duckdb
import pandas as pd

from . import fill
from .loaders import (
    FORMER_STATE_NAMES,
    FORMER_STATES,
    load_maddison,
    load_maddison_regional_benchmarks,
    load_maddison_world_benchmarks,
    load_pwt,
    load_wdi,
    load_wpp,
)
from .paths import PROCESSED_DIR

START_YEAR = 1500
MADDISON_LAST_YEAR = 2022
# Lowest plausible GDP per person (2011 $): roughly bare subsistence. Estimated values never go below it.
SUBSISTENCE_FLOOR = 400.0
# A year counts as "covered" by WDI when at least this many countries report it.
MIN_COUNTRIES_FOR_YEAR = 150


def _wide(df: pd.DataFrame, col: str) -> pd.DataFrame:
    return df.pivot_table(index="year", columns="iso3", values=col, aggfunc="first")


def _fill_maddison(maddison: pd.DataFrame, regions: pd.Series,
                   col: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fill one variable for every country, 1500-2022. Returns (values, flags, former_states)."""
    raw = _wide(maddison, col)
    all_years = sorted(set(raw.index) | set(range(START_YEAR, MADDISON_LAST_YEAR + 1)))
    vals, flags = fill.interpolate_log(raw.reindex(all_years))
    years = list(range(START_YEAR, MADDISON_LAST_YEAR + 1))
    vals, flags = vals.loc[years], flags.loc[years]

    parents = vals[[c for c in FORMER_STATES if c in vals.columns]]
    countries = [c for c in vals.columns if c not in FORMER_STATES]
    vals, flags = vals[countries], flags[countries]

    region_g = fill.group_median_growth(vals, regions)
    world_g = fill.median_growth(vals)
    parent_g = fill.growth(parents)
    parent_of = {child: p for p, kids in FORMER_STATES.items() for child in kids}

    out_v, out_f = {}, {}
    for c in countries:
        ref = region_g[regions[c]] if regions.get(c) in region_g.columns else world_g
        ref = ref.combine_first(world_g)
        label = pd.Series(fill.REGIONAL, index=vals.index, dtype=object)
        if c in parent_of and parent_of[c] in parent_g.columns:
            pg = parent_g[parent_of[c]]
            label[pg.notna()] = fill.PARENT
            ref = pg.combine_first(ref)
        out_v[c], out_f[c] = fill.extend_with_growth(vals[c], flags[c], ref, label)
    return pd.DataFrame(out_v), pd.DataFrame(out_f), parents


def _calibrate_regions(gdppc, gdppc_f, pop, pop_f, regions, bench):
    """Make each region's estimated countries add up to Maddison's published regional totals."""
    pop_target = bench.pivot_table(index="year", columns="region", values="pop")
    gdp_target = bench.pivot_table(index="year", columns="region", values="gdp")
    pop, pop_factors = fill.calibrate_to_totals(pop, pop_f, regions, pop_target)
    gdppc, gdp_factors = fill.calibrate_to_totals(gdppc, gdppc_f, regions, gdp_target, weight=pop)
    estimated = gdppc_f.isin([fill.PARENT, fill.REGIONAL])
    gdppc = gdppc.mask(estimated & (gdppc < SUBSISTENCE_FLOOR), SUBSISTENCE_FLOOR)
    factors = pd.concat({"pop": pop_factors, "gdppc": gdp_factors}, names=["variable", "year"])
    return gdppc, pop, factors


def _latest_wdi_year(wdi: pd.DataFrame) -> int:
    counts = wdi.dropna(subset=["gdppc_ppp_const"]).groupby("year").size()
    return int(counts[counts >= MIN_COUNTRIES_FOR_YEAR].index.max())


def _extend_recent(vals: pd.DataFrame, flags: pd.DataFrame, source_wide: pd.DataFrame,
                   regions: pd.Series, end_year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carry each country from 2022 to `end_year` using growth rates from a newer source."""
    years = list(range(START_YEAR, end_year + 1))
    vals, flags = vals.reindex(years), flags.reindex(years)
    src = source_wide.reindex(index=years, columns=vals.columns)
    g = fill.growth(src)
    region_g = fill.group_median_growth(src, regions)
    new = [y for y in years if y > MADDISON_LAST_YEAR]
    for c in vals.columns:
        gc = g[c]
        if regions.get(c) in region_g.columns:  # country missing from the source: use its region's median
            gc = gc.combine_first(region_g[regions[c]])
        v, f = fill.extend_with_growth(vals[c], flags[c], gc, fill.EXTENDED, backward=False)
        vals.loc[new, c], flags.loc[new, c] = v[new], f[new]
    return vals, flags


def _long(wide: pd.DataFrame, name: str) -> pd.Series:
    s = wide.stack(future_stack=True)
    s.index.names = ["year", "iso3"]
    return s.rename(name)


def build_history() -> dict[str, pd.DataFrame]:
    maddison, mcountries = load_maddison()
    wdi, wdi_meta = load_wdi()
    wpp = load_wpp()
    regions = mcountries.set_index("iso3")["region"]

    gdppc, gdppc_f, parents_gdppc = _fill_maddison(maddison, regions, "gdppc")
    pop, pop_f, parents_pop = _fill_maddison(maddison, regions, "pop")
    bench = load_maddison_regional_benchmarks()
    gdppc, pop, factors = _calibrate_regions(gdppc, gdppc_f, pop, pop_f, regions, bench)

    end_year = _latest_wdi_year(wdi)
    gdppc, gdppc_f = _extend_recent(gdppc, gdppc_f, _wide(wdi, "gdppc_ppp_const"), regions, end_year)
    pop, pop_f = _extend_recent(pop, pop_f, _wide(wpp, "pop"), regions, end_year)

    hist = pd.concat([_long(gdppc, "gdppc"), _long(pop, "pop"),
                      _long(gdppc_f, "gdppc_flag"), _long(pop_f, "pop_flag")], axis=1).reset_index()
    hist["gdp"] = hist["gdppc"] * hist["pop"]
    hist["flag"] = fill.worst_flag(hist["gdppc_flag"], hist["pop_flag"])
    hist = hist[["iso3", "year", "gdppc", "pop", "gdp", "gdppc_flag", "pop_flag", "flag"]]
    hist = hist.sort_values(["iso3", "year"]).reset_index(drop=True)

    countries = (mcountries[~mcountries["iso3"].isin(FORMER_STATES)]
                 .rename(columns={"country": "name", "region": "maddison_region"})
                 .merge(wdi_meta[["iso3", "wb_region", "income_group"]], on="iso3", how="left"))
    countries["former_state"] = countries["iso3"].map(
        {k: p for p, kids in FORMER_STATES.items() for k in kids})

    former = pd.concat([_long(parents_gdppc, "gdppc"), _long(parents_pop, "pop")], axis=1).reset_index()
    former["gdp"] = former["gdppc"] * former["pop"]
    former["name"] = former["iso3"].map(FORMER_STATE_NAMES)

    return {
        "history": hist,
        "countries": countries,
        "former_states": former.dropna(subset=["gdppc", "pop"], how="all"),
        "regional_benchmarks": bench,
        "calibration_factors": factors.reset_index(),
        "population_un": wpp,
        "pwt": load_pwt(),
        "world_benchmarks": load_maddison_world_benchmarks(),
    }


def write_parquet(tables: dict[str, pd.DataFrame]) -> None:
    con = duckdb.connect()
    for name, df in tables.items():
        path = (PROCESSED_DIR / f"{name}.parquet").as_posix()
        con.register("t", df)
        con.execute(f"COPY t TO '{path}' (FORMAT parquet, COMPRESSION zstd)")
        con.unregister("t")
        print(f"  wrote {name}.parquet  ({len(df):,} rows)")


def read_parquet(name: str) -> pd.DataFrame:
    path = (PROCESSED_DIR / f"{name}.parquet").as_posix()
    return duckdb.sql(f"SELECT * FROM '{path}'").df()
