# World GDP Dashboard

500 years of GDP for the world's economies (1500 to today), plus a simulator that projects the next
100 years. You adjust the drivers of growth (population, investment, education, technology,
catch-up speed, trade, climate) country by country or for whole groups of countries.

**Status:** Milestones 1-2 of 7 done: the joined history dataset and the history dashboard.
See [docs/plan.md](docs/plan.md).

## Folder layout

| Folder | What's in it |
|---|---|
| `pipeline/` | Python code that downloads public data and builds the history dataset |
| `gdpsim/` | *(next)* the growth model, as a Python package |
| `api/` | FastAPI web server: serves the data, and the built dashboard |
| `app/` | React + TypeScript dashboard (map, time series, share of world, rankings) |
| `notebooks/` | Jupyter notebooks for calibration and analysis |
| `docs/` | Plan, method notes, and the data quality report |
| `data/raw/` | Downloaded files, exactly as published (not saved in Git) |
| `data/processed/` | Cleaned Parquet files built by the pipeline (not saved in Git) |

## Running the dashboard

The data must be built first (see *Getting started* below).

```powershell
cd C:\Users\shail\workbench\gdp-dashboard
cd app; npm install; npm run build; cd ..   # one-off, and again after changing code in app/
uv run python -m api                        # then open http://127.0.0.1:8000
```

Stop it with Ctrl+C. Options: `--port 8080`, and `--reload` to restart when Python code changes.
API docs are at http://127.0.0.1:8000/docs. The address bar keeps the current view
(e.g. `?year=1820&metric=gdp&group=income_group&c=CHN,IND,GBR`), so views can be bookmarked.

**While editing the dashboard code**, use two terminals for instant reloads:

```powershell
uv run python -m api          # terminal 1: data server on port 8000
cd app; npm run dev           # terminal 2: open the address it prints (http://localhost:5173)
```

## Getting started

You need Git, Python 3.12 (from python.org), [uv](https://docs.astral.sh/uv/) and
[Node.js](https://nodejs.org/) (for the dashboard).

```powershell
cd C:\Users\shail\workbench\gdp-dashboard
uv sync                                    # one-off: install the Python libraries
cd pipeline
uv run python -m gdp_pipeline              # download all data and build (a few minutes)
uv run python -m gdp_pipeline build        # rebuild only, using files already downloaded
cd ..
uv run pytest                              # run the tests (pipeline and API)
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
