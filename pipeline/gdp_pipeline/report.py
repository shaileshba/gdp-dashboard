"""Write docs/data_quality_report.md: how much of the history is real data vs estimate, plus sanity checks."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from . import fill
from .paths import DOCS_DIR, RAW_DIR

BENCHMARK_YEARS = [1500, 1600, 1700, 1820, 1870, 1913, 1950, 1990, 2022]
GOOD = {fill.OBSERVED, fill.INTERPOLATED, fill.EXTENDED}


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def _coverage(hist: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    rows = []
    for y in years:
        h = hist[hist["year"] == y]
        total = h["gdp"].sum()
        rows.append({
            "Year": y,
            "Countries with observed GDP/head": int((h["gdppc_flag"] == fill.OBSERVED).sum()),
            "World GDP from real data (obs./interp.)": f"{h.loc[h['flag'].isin(GOOD), 'gdp'].sum() / total:.0%}",
            "World GDP from estimates": f"{h.loc[~h['flag'].isin(GOOD), 'gdp'].sum() / total:.0%}",
        })
    return pd.DataFrame(rows)


def _benchmark_check(hist: pd.DataFrame, bench: pd.DataFrame) -> pd.DataFrame:
    world = hist.groupby("year").agg(gdp=("gdp", "sum"), pop=("pop", "sum"))
    world["gdppc"] = world["gdp"] / world["pop"]
    b = bench.dropna(subset=["world_gdppc"]).set_index("year")
    b = b[b.index.isin(world.index)]
    out = pd.DataFrame({
        "Year": b.index,
        "Maddison world GDP/head": b["world_gdppc"].round(0).astype(int).values,
        "Our world GDP/head": world.loc[b.index, "gdppc"].round(0).astype(int).values,
        "Maddison world pop (m)": (b["world_pop"] / 1e6).round(0).values,
        "Our world pop (m)": (world.loc[b.index, "pop"] / 1e6).round(0).values,
    })
    out["GDP/head gap"] = (out["Our world GDP/head"] / out["Maddison world GDP/head"] - 1).map("{:+.1%}".format)
    return out


def _regional_check(hist: pd.DataFrame, countries: pd.DataFrame, bench: pd.DataFrame,
                    years=(1820, 1870, 1913, 1950)) -> pd.DataFrame:
    h = hist.merge(countries[["iso3", "maddison_region"]], on="iso3")
    ours = h.groupby(["year", "maddison_region"]).agg(gdp=("gdp", "sum"), pop=("pop", "sum"))
    rows = []
    for y in years:
        for r in bench[(bench["year"] == y)].dropna(subset=["gdppc", "pop"]).itertuples():
            o = ours.loc[(y, r.region)]
            rows.append({"Year": y, "Region": r.region,
                         "GDP/head ours vs Maddison": f"{o.gdp / o['pop']:,.0f} vs {r.gdppc:,.0f}",
                         "Pop gap": f"{o['pop'] / r.pop - 1:+.1%}",
                         "GDP gap": f"{o.gdp / r.gdp - 1:+.1%}"})
    return pd.DataFrame(rows)


def _top(hist: pd.DataFrame, countries: pd.DataFrame, year: int, n: int = 8) -> str:
    h = hist[hist["year"] == year].merge(countries[["iso3", "name"]], on="iso3")
    h["share"] = h["gdp"] / h["gdp"].sum()
    h = h.nlargest(n, "gdp")
    return ", ".join(f"{r.name} {r.share:.0%}" + ("" if r.flag in GOOD else "*")
                     for r in h.itertuples())


def write_report(tables: dict[str, pd.DataFrame]) -> str:
    hist, countries = tables["history"], tables["countries"]
    manifest = json.loads((RAW_DIR / "manifest.json").read_text())
    end = int(hist["year"].max())

    flag_counts = (hist["flag"].value_counts(normalize=True).rename("Share of country-years")
                   .map("{:.1%}".format).rename_axis("Label").reset_index())

    # Sanity checks
    problems = []
    if hist.duplicated(["iso3", "year"]).any():
        problems.append("duplicate country-year rows")
    if hist[["gdppc", "pop"]].isna().any().any():
        problems.append(f"{int(hist[['gdppc', 'pop']].isna().any(axis=1).sum())} rows with missing values")
    if (hist[["gdppc", "pop"]] <= 0).any().any():
        problems.append("zero or negative values")
    g = hist.sort_values(["iso3", "year"]).groupby("iso3")["gdppc"].transform(lambda s: np.log(s).diff())
    jumps = hist.assign(g=g).loc[g.abs() > np.log(1.4)].merge(countries[["iso3", "name"]], on="iso3")
    jumps = jumps.reindex(jumps["g"].abs().sort_values(ascending=False).index).head(12)
    jump_txt = ", ".join(f"{r.name} {r.year} ({np.exp(r.g) - 1:+.0%})" for r in jumps.itertuples())
    no_wb = countries.loc[countries["wb_region"].isna(), "name"].tolist()

    md = f"""# Data quality report

Generated {date.today().isoformat()} by `uv run python -m gdp_pipeline build`.

**Coverage:** {hist['iso3'].nunique()} countries, {int(hist['year'].min())}-{end}, {len(hist):,} country-years.
Units: GDP per person in **2011 international dollars (PPP)**; population in persons; borders as of today.

## How each value was produced

| Label | Meaning |
|---|---|
| observed | Value is in the Maddison Project Database |
| interpolated | Between two observed years, assuming steady growth |
| extended | After 2022, follows World Bank (GDP/head) or UN (population) growth rates |
| parent | Before the country appears, follows the former state it belonged to (USSR, Czechoslovakia, Yugoslavia) |
| regional | Outside the observed years, follows the median growth of other countries in its region |

A country-year's overall label is the weaker of its GDP/head and population labels.

Two adjustments apply to *regional* estimates only (real data is never changed):
- **Calibration to Maddison's regional totals.** Where Maddison publishes a total for a region
  (1820 onward), estimated countries in that region are scaled so the region adds up. The scaling
  is held flat before 1820, and fades out over 30 years as an estimate approaches a country's
  first real data point, so the two join without a jump.
- **Subsistence floor.** Estimated GDP per person never falls below $400.

{_md_table(flag_counts)}

## How much of world GDP rests on real data

{_md_table(_coverage(hist, BENCHMARK_YEARS + ([end] if end not in BENCHMARK_YEARS else [])))}

Before 1820, most of the world total is estimated. Charts should show this (e.g. dashed lines).

## Check against Maddison's own world totals

{_md_table(_benchmark_check(hist, tables['world_benchmarks']))}

### By region

{_md_table(_regional_check(hist, countries, tables['regional_benchmarks']))}

Remaining gaps come from two places: the 30-year fade (estimates close to real data are scaled
less), and Eastern Europe, where Maddison's newer Russia series is lower than its own USSR total.
We keep the Russia series as published rather than force it to match.

## Largest economies (share of world GDP; * = estimated)

""" + "\n".join(f"- **{y}:** {_top(hist, countries, y)}" for y in [1500, 1700, 1820, 1913, 1950, end]) + f"""

## Sanity checks

- Structural problems: {', '.join(problems) if problems else 'none found'}
- Year-on-year GDP/head moves larger than 40% (usually wars, oil states or data breaks; review these):
  {jump_txt or 'none'}
- Countries without a World Bank region/income group: {', '.join(no_wb) if no_wb else 'none'}

## Known gaps / next steps

- About 50 small economies in the World Bank list are not in Maddison and are not yet included
  (together well under 1% of world GDP).
- Before 1947, India, Pakistan and Bangladesh are split out of Maddison's British India total
  in proportion to their populations and incomes just after Partition.
- Ireland's series before 1921 includes Northern Ireland (about 1.3 million people double-counted
  with the UK); too small to matter at world level, noted for country views.
- Age structure (working-age share) from UN WPP is needed for the labour lever; it is added in the model milestone.

## Sources

""" + "\n".join(f"- `{k}`: {v['url']} (downloaded {v['downloaded_at'][:10]}, sha256 {v['sha256'][:12]}...)"
                for k, v in manifest.items()) + "\n"

    path = DOCS_DIR / "data_quality_report.md"
    path.write_text(md, encoding="utf-8")
    return str(path)
