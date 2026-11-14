"""Turn sparse historical observations into a complete annual series, labelling every value.

All functions work on "wide" tables: one row per year, one column per country (ISO3 code).

How a gap is filled, from best to worst:
  observed       the value is in the source data
  interpolated   between two observed years, assuming steady growth (straight line in logs)
  parent         before a country existed in the data, borrow the growth of the larger unit it
                 was part of (e.g. Ukraine before 1990 follows the former USSR)
  regional       outside the observed span, borrow the typical (median) growth of other
                 countries in the same region that year
  extended       after the last Maddison year, follow growth from a newer source (WDI / UN WPP)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

OBSERVED, INTERPOLATED, PARENT, REGIONAL, EXTENDED = (
    "observed", "interpolated", "parent", "regional", "extended",
)
# Lower = more reliable. Used to report the weakest label when combining GDP per head and population.
FLAG_RANK = {OBSERVED: 0, INTERPOLATED: 1, EXTENDED: 1, PARENT: 2, REGIONAL: 3}


def interpolate_log(wide: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill gaps *between* observations with constant growth. Returns (values, flags)."""
    flags = pd.DataFrame(np.where(wide.notna(), OBSERVED, None), index=wide.index, columns=wide.columns)
    filled = np.exp(np.log(wide).interpolate(method="index", limit_area="inside"))
    flags = flags.mask(flags.isna() & filled.notna(), INTERPOLATED)
    return filled, flags


def growth(wide: pd.DataFrame) -> pd.DataFrame:
    """Year-on-year log growth: g[t] = ln(x[t]) - ln(x[t-1])."""
    return np.log(wide).diff()


MIN_COUNTRIES_FOR_MEDIAN = 3


def median_growth(wide: pd.DataFrame, min_countries: int = MIN_COUNTRIES_FOR_MEDIAN) -> pd.Series:
    """Median growth per year across all columns; NaN where fewer than `min_countries` report."""
    g = growth(wide)
    return g.median(axis=1).where(g.notna().sum(axis=1) >= min_countries)


def group_median_growth(wide: pd.DataFrame, groups: pd.Series,
                        min_countries: int = MIN_COUNTRIES_FOR_MEDIAN) -> pd.DataFrame:
    """Median growth per year within each group (columns = group names).

    `groups` maps country code -> group name. Only countries with a value in both years count,
    so the result reflects real (observed or interpolated) data only. A group-year with fewer
    than `min_countries` is left blank: one or two unusual countries should not set the path
    for a whole region.
    """
    g = growth(wide)
    by = g.T.groupby(groups.reindex(g.columns))
    return by.median().T.where(by.count().T >= min_countries)


def extend_with_growth(values: pd.Series, flags: pd.Series, ref_growth: pd.Series,
                       label: str | pd.Series, backward: bool = True,
                       forward: bool = True) -> tuple[pd.Series, pd.Series]:
    """Extend a series beyond its first/last value by following a reference growth path.

    `label` is the flag written on each filled year: one string, or a per-year Series when the
    reference growth is stitched together from several sources. Years where the reference
    growth is unknown are treated as zero growth (level held flat).
    """
    v, f = values.copy(), flags.copy().astype(object)
    known = v.dropna()
    if known.empty:
        return v, f
    years = v.index
    g = ref_growth.reindex(years).fillna(0.0).to_numpy()
    lab = (label.reindex(years).fillna(REGIONAL).to_numpy() if isinstance(label, pd.Series)
           else np.full(len(years), label, dtype=object))
    x = v.to_numpy(dtype=float).copy()
    fl = f.to_numpy(dtype=object).copy()
    first, last = years.get_loc(known.index[0]), years.get_loc(known.index[-1])
    if backward:
        for i in range(first - 1, -1, -1):  # walk back: x[t] = x[t+1] / exp(g[t+1])
            x[i] = x[i + 1] / np.exp(g[i + 1])
            fl[i] = lab[i + 1]
    if forward:
        for i in range(last + 1, len(years)):  # walk forward: x[t] = x[t-1] * exp(g[t])
            x[i] = x[i - 1] * np.exp(g[i])
            fl[i] = lab[i]
    return pd.Series(x, index=years, name=v.name), pd.Series(fl, index=years, name=f.name)


def _distance_to_anchor(adjustable: np.ndarray) -> np.ndarray:
    """For each year, how many years away the nearest non-adjustable (real-data) year is."""
    n = len(adjustable)
    anchors = np.flatnonzero(~adjustable)
    if anchors.size == 0:
        return np.full(n, np.inf)
    idx = np.arange(n)
    pos = np.clip(np.searchsorted(anchors, idx), 1, anchors.size) - 1
    left = np.abs(idx - anchors[pos])
    right = np.abs(anchors[np.clip(pos + 1, 0, anchors.size - 1)] - idx)
    return np.minimum(left, right).astype(float)


def calibrate_to_totals(vals: pd.DataFrame, flags: pd.DataFrame, groups: pd.Series,
                        target: pd.DataFrame, weight: pd.DataFrame | None = None,
                        adjustable: str = REGIONAL, fade_years: int = 30,
                        bounds: tuple[float, float] = (1 / 3, 3.0)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Scale *estimated* values so each group's total matches a published benchmark.

    vals    years x countries, the variable being scaled (population, or GDP per person)
    weight  multiplier that turns vals into the summed quantity (population, when vals is GDP
            per person, so the totals compared are GDP). None = sum vals directly.
    target  years x groups benchmark totals (NaN where no benchmark exists)

    Only values flagged `adjustable` change. The scaling factor is worked out at benchmark years,
    interpolated between them, and held flat outside them. For each country the factor fades out
    linearly over `fade_years` as it nears real data, so estimates join real data without a jump.
    Returns (scaled values, factors by year x group).
    """
    q = vals if weight is None else vals * weight
    adj = flags == adjustable
    out = vals.copy()
    factors = pd.DataFrame(1.0, index=vals.index, columns=target.columns)
    for grp in target.columns:
        cols = [c for c in vals.columns if groups.get(c) == grp]
        if not cols:
            continue
        fixed = q[cols].where(~adj[cols]).sum(axis=1)
        est = q[cols].where(adj[cols]).sum(axis=1)
        t = target[grp].reindex(vals.index)
        ok = t.notna() & (est > 0) & (t > fixed)
        if not ok.any():
            continue
        f = ((t - fixed) / est).where(ok).clip(*bounds)
        logf = np.log(f).interpolate(method="index", limit_area="inside").ffill().bfill()
        factors[grp] = np.exp(logf)
        for c in cols:
            a = adj[c].to_numpy()
            if not a.any():
                continue
            w = np.clip(_distance_to_anchor(a) / fade_years, 0, 1)
            scale = np.where(a, np.exp(logf.to_numpy() * w), 1.0)
            out[c] = vals[c] * scale
    return out, factors


def worst_flag(a: pd.Series, b: pd.Series) -> pd.Series:
    """For each row, the less reliable of two labels."""
    ra, rb = a.map(FLAG_RANK), b.map(FLAG_RANK)
    return a.where(ra >= rb, b)
