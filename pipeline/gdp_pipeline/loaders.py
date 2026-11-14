"""Read each raw file into a tidy table (one row per country-year)."""

from __future__ import annotations

import pandas as pd

from .paths import RAW_DIR

# Maddison lists these former states as combined totals right up to 2022, *alongside* their
# successor countries. Adding everything up would count those economies twice, so the totals
# are kept only as a guide for the successors' early years.
FORMER_STATES = {
    "SUN": ["ARM", "AZE", "BLR", "EST", "GEO", "KAZ", "KGZ", "LTU", "LVA", "MDA",
            "RUS", "TJK", "TKM", "UKR", "UZB"],
    "CSK": ["CZE", "SVK"],
    "YUG": ["BIH", "HRV", "MKD", "MNE", "SRB", "SVN"],
    # Maddison's "India" before 1947 is all of British India (it drops 17% at Partition), so
    # those years are moved into this combined total and shared out like the other former states.
    "BRI": ["IND", "PAK", "BGD"],
}
FORMER_STATE_NAMES = {"SUN": "Former USSR", "CSK": "Czechoslovakia", "YUG": "Former Yugoslavia",
                      "BRI": "British India (pre-1947)"}
PARTITION_YEAR = {"BRI": ("IND", 1947)}  # (country whose early data is the combined total, first own year)


def load_maddison() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (data, countries). Units: GDP per person in 2011 international $ (PPP); persons."""
    df = pd.read_excel(RAW_DIR / "mpd2023_web.xlsx", sheet_name="Full data")
    df = df.rename(columns={"countrycode": "iso3"})
    df["pop"] = df["pop"] * 1000  # source is in thousands
    for agg, (iso3, first_year) in PARTITION_YEAR.items():
        early = (df["iso3"] == iso3) & (df["year"] < first_year)
        df.loc[early, "iso3"] = agg
    countries = (df.loc[~df["iso3"].isin(PARTITION_YEAR), ["iso3", "country", "region"]]
                 .drop_duplicates("iso3").reset_index(drop=True))
    return df[["iso3", "year", "gdppc", "pop"]], countries


def _regional_sheet() -> pd.DataFrame:
    return pd.read_excel(RAW_DIR / "mpd2023_web.xlsx", sheet_name="Regional data", header=None)


def load_maddison_world_benchmarks() -> pd.DataFrame:
    """Maddison's own world GDP per person, used to check our aggregates."""
    r = _regional_sheet()
    out = r.iloc[2:, [0, 9, 19]]
    out.columns = ["year", "world_gdppc", "world_pop"]
    out = out.dropna(subset=["year"]).astype({"year": int})
    out["world_pop"] = pd.to_numeric(out["world_pop"], errors="coerce") * 1000
    out["world_gdppc"] = pd.to_numeric(out["world_gdppc"], errors="coerce")
    return out.reset_index(drop=True)


def load_maddison_regional_benchmarks() -> pd.DataFrame:
    """Maddison's published totals for its 8 regions (1820 onward, some years only).

    Columns 1-8 hold GDP per person and 11-18 population for the same regions in the same order.
    Returns long table: year, region, gdppc, pop (persons), gdp.
    """
    r = _regional_sheet()
    regions = r.iloc[1, 1:9].tolist()
    body = r.iloc[2:].dropna(subset=[0])
    rows = []
    for i, reg in enumerate(regions):
        rows.append(pd.DataFrame({
            "year": body[0].astype(int).values, "region": reg,
            "gdppc": pd.to_numeric(body[1 + i], errors="coerce").values,
            "pop": pd.to_numeric(body[11 + i], errors="coerce").values * 1000,
        }))
    out = pd.concat(rows, ignore_index=True)
    out["gdp"] = out["gdppc"] * out["pop"]
    return out


def load_wdi() -> tuple[pd.DataFrame, pd.DataFrame]:
    wdi = pd.read_csv(RAW_DIR / "wdi_gdp.csv")
    wide = wdi.pivot_table(index=["iso3", "year"], columns="indicator", values="value").reset_index()
    meta = pd.read_csv(RAW_DIR / "wdi_countries.csv")
    meta = meta[~meta["is_aggregate"]].drop(columns="is_aggregate")
    return wide, meta


def load_wpp() -> pd.DataFrame:
    """UN population estimates (1950-2023) and medium-variant projections (2024-2100)."""
    cols = ["ISO3_code", "LocTypeName", "Time", "TPopulation1July", "TFR", "LEx",
            "MedianAgePop", "NetMigrations", "PopGrowthRate"]
    w = pd.read_csv(RAW_DIR / "WPP2024_Demographic_Indicators_Medium.csv.gz", usecols=cols,
                    dtype={"ISO3_code": str, "LocTypeName": str})
    w = w[w["LocTypeName"] == "Country/Area"].drop(columns="LocTypeName")
    w = w.rename(columns={"ISO3_code": "iso3", "Time": "year", "TPopulation1July": "pop",
                          "TFR": "fertility", "LEx": "life_expectancy", "MedianAgePop": "median_age",
                          "NetMigrations": "net_migration", "PopGrowthRate": "pop_growth_pct"})
    w["pop"] = w["pop"] * 1000  # source is in thousands
    w["net_migration"] = w["net_migration"] * 1000
    return w.reset_index(drop=True)


def load_pwt() -> pd.DataFrame:
    """Penn World Table: the inputs the growth model is calibrated on (1950-2023)."""
    keep = {
        "countrycode": "iso3", "year": "year",
        "rgdpna": "gdp_real",          # real GDP at constant national prices (2021 US$ millions)
        "rnna": "capital_real",        # capital stock at constant national prices
        "emp": "employment",           # persons engaged (millions)
        "avh": "hours_per_worker",     # average annual hours worked
        "hc": "human_capital",         # index from years of schooling and returns to education
        "labsh": "labour_share",       # share of labour income in GDP
        "rtfpna": "tfp_index",         # productivity (TFP), 2021 = 1
        "csh_i": "investment_share",   # investment as a share of GDP
        "delta": "depreciation",       # rate at which capital wears out
        "pop": "pop_millions",
    }
    p = pd.read_excel(RAW_DIR / "pwt110.xlsx", sheet_name="Data", usecols=list(keep))
    return p.rename(columns=keep)
