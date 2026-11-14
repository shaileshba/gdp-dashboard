# World GDP Dashboard

500 years of GDP for the world's economies (1500 to today), plus a simulator that projects the next
100 years. You adjust the drivers of growth (population, investment, education, technology,
catch-up speed, trade, climate) country by country or for whole groups of countries.

**Status:** Milestone 1 of 7 done: the joined history dataset. See [docs/plan.md](docs/plan.md).

## Folder layout

| Folder | What's in it |
|---|---|
| `pipeline/` | Python code that downloads public data and builds the history dataset |
| `gdpsim/` | *(next)* the growth model, as a Python package |
| `api/` | *(next)* FastAPI web server that runs the model for the dashboard |
| `app/` | *(next)* React dashboard |
| `notebooks/` | Jupyter notebooks for calibration and analysis |
| `docs/` | Plan, method notes, and the data quality report |
| `data/raw/` | Downloaded files, exactly as published (not saved in Git) |
| `data/processed/` | Cleaned Parquet files built by the pipeline (not saved in Git) |

## Getting started

You need Git, Python 3.12 (from python.org) and [uv](https://docs.astral.sh/uv/).

```powershell
cd C:\Users\shail\workbench\gdp-dashboard
uv sync                                    # one-off: install the Python libraries
cd pipeline
uv run python -m gdp_pipeline              # download all data and build (a few minutes)
uv run python -m gdp_pipeline build        # rebuild only, using files already downloaded
cd ..
uv run pytest                              # run the tests
```

The build writes `data/processed/*.parquet` and refreshes
[docs/data_quality_report.md](docs/data_quality_report.md).

## Data sources

| Dataset | Used for | License |
|---|---|---|
| Maddison Project Database 2023 | GDP per person and population, 1500-2022 | CC BY 4.0 |
| World Bank World Development Indicators | GDP growth after 2022; country regions and income groups | CC BY 4.0 |
| UN World Population Prospects 2024 | Population after 2022; population and fertility projections to 2100 | CC BY 3.0 IGO |
| Penn World Table 11.0 | Capital, employment, education and productivity (for model calibration) | CC BY 4.0 |

All values are in **2011 international dollars (PPP)** within present-day borders.
Every value is labelled `observed`, `interpolated`, `extended`, `parent` or `regional`, so the
dashboard can show which numbers are measured and which are estimated.
See the [data quality report](docs/data_quality_report.md) for details.

## Windows note: Smart App Control

This PC has Windows Smart App Control turned on, which blocks unsigned programs.
Two consequences:
- Use Python from python.org, not uv's own Python download. uv is set to `UV_PYTHON_PREFERENCE=only-system`.
- `pyarrow` is blocked, so the project doesn't use it. Parquet files are read and written with DuckDB instead.
