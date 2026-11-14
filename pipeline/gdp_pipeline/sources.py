"""Where each dataset comes from, and the code that downloads it.

Every download is recorded in data/raw/manifest.json (URL, size, SHA-256 checksum,
date) so we always know exactly which version of each dataset a result was built from.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
import requests

from .paths import RAW_DIR

MANIFEST = RAW_DIR / "manifest.json"
HEADERS = {"User-Agent": "gdp-dashboard-pipeline/0.1"}


@dataclass(frozen=True)
class FileSource:
    key: str
    filename: str
    url: str
    citation: str
    license: str


FILE_SOURCES = [
    FileSource(
        key="maddison",
        filename="mpd2023_web.xlsx",
        url="https://dataverse.nl/api/access/datafile/421302",
        citation="Bolt, J. and van Zanden, J.L. (2024). Maddison style estimates of the evolution "
        "of the world economy: A new 2023 update. Journal of Economic Surveys. doi:10.34894/INZBF2",
        license="CC BY 4.0",
    ),
    FileSource(
        key="pwt",
        filename="pwt110.xlsx",
        url="https://dataverse.nl/api/access/datafile/554105",
        citation="Feenstra, R.C., Inklaar, R. and Timmer, M.P., Penn World Table version 11.0 "
        "(2025). Groningen Growth and Development Centre. doi:10.34894/FABVLR",
        license="CC BY 4.0",
    ),
    FileSource(
        key="wpp",
        filename="WPP2024_Demographic_Indicators_Medium.csv.gz",
        url="https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/"
        "CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz",
        citation="United Nations, DESA, Population Division (2024). World Population Prospects 2024.",
        license="CC BY 3.0 IGO",
    ),
]

# World Bank World Development Indicators, fetched from its free JSON API.
WDI_INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "gdppc_ppp_const",  # GDP per person, PPP, constant international $
    "NY.GDP.MKTP.PP.KD": "gdp_ppp_const",  # total GDP, PPP, constant international $
}
WDI_CITATION = "World Bank (2026). World Development Indicators."
WDI_LICENSE = "CC BY 4.0"
WDI_FIRST_YEAR = 2010


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _record(manifest: dict, key: str, filename: str, url: str) -> None:
    path = RAW_DIR / filename
    manifest[key] = {
        "file": filename,
        "url": url,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def _download(url: str, dest) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(dest)


def _wdi_pages(url: str, **params) -> list[dict]:
    """Read every page of a World Bank API JSON response."""
    rows, page = [], 1
    while True:
        r = requests.get(url, params={"format": "json", "per_page": 20000, "page": page, **params},
                         headers=HEADERS, timeout=120)
        r.raise_for_status()
        meta, data = r.json()
        rows.extend(data or [])
        if page >= meta["pages"]:
            return rows
        page += 1


def fetch_wdi(manifest: dict) -> None:
    # Country list: names, regions and income groups (used later for country groups).
    countries = _wdi_pages("https://api.worldbank.org/v2/country")
    meta = pd.DataFrame(
        {
            "iso3": c["id"],
            "name": c["name"],
            "wb_region": c["region"]["value"],
            "income_group": c["incomeLevel"]["value"],
            "is_aggregate": c["region"]["value"] == "Aggregates",
        }
        for c in countries
    )
    meta.to_csv(RAW_DIR / "wdi_countries.csv", index=False)
    _record(manifest, "wdi_countries", "wdi_countries.csv", "https://api.worldbank.org/v2/country")

    last_year = datetime.now().year
    frames = []
    for code, name in WDI_INDICATORS.items():
        rows = _wdi_pages(f"https://api.worldbank.org/v2/country/all/indicator/{code}",
                          date=f"{WDI_FIRST_YEAR}:{last_year}")
        frames.append(pd.DataFrame(
            {"iso3": x["countryiso3code"], "year": int(x["date"]), "indicator": name, "value": x["value"]}
            for x in rows if x["countryiso3code"]
        ))
    wdi = pd.concat(frames).dropna(subset=["value"])
    wdi.to_csv(RAW_DIR / "wdi_gdp.csv", index=False)
    _record(manifest, "wdi_gdp", "wdi_gdp.csv", "https://api.worldbank.org/v2/ " + ", ".join(WDI_INDICATORS))


def fetch_all(force: bool = False) -> dict:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for s in FILE_SOURCES:
        dest = RAW_DIR / s.filename
        if force or not dest.exists():
            print(f"  downloading {s.key} ...")
            _download(s.url, dest)
        else:
            print(f"  {s.key}: already downloaded")
        _record(manifest, s.key, s.filename, s.url)
    print("  fetching World Bank WDI via API ...")
    fetch_wdi(manifest)
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest
