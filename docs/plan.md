# Project plan

**Goal:** an analyst dashboard of GDP for every economy from 1500 to today, plus a 100-year
scenario simulator with growth drivers (levers) adjustable per country and per group.
It starts as a personal tool running on this PC and becomes a public website later.

## Decisions so far

- **Users:** analysts. Levers can be set per country and edited in bulk for groups.
- **Lever settings stack:** global → group → country, and the most specific setting wins. Each lever is a path
  over time (start value, target value, year reached, curve shape), not a single number.
- **Stack:** Python (data pipeline, model, FastAPI) and React + TypeScript (dashboard). The model lives in
  one Python package, `gdpsim`, so notebooks, the API and calibration always give the same numbers.
- **Storage:** Parquet files for data (via DuckDB). SQLite for saved scenarios now, Postgres when public.
- **Hosting:** runs on this PC (localhost) for now, so no login is needed. Phase 2 (share privately)
  would add a login, using a Microsoft account or Cloudflare Access. Phase 3 is a public read-only site.

## Growth model (Milestone 3)

Augmented Solow model, run for each country: `Y = A · K^α · (h·L)^(1-α)`

- A (productivity) = frontier growth + catch-up × (gap to frontier) + trade/institutions effect − climate damage
- K (capital) builds up from investment and wears out (depreciation)
- L (workers) = UN population × working-age share × participation
- h (human capital) comes from years of schooling

Levers: fertility/population, participation and retirement age, investment rate, education,
frontier productivity growth (incl. AI), catch-up speed (institutions), trade openness, climate
(warming × damage), optional energy and debt. Calibrated on 1950-2000, tested on 2000-2022, with
the baseline aligned to SSP2. SSP1-5 come as presets. Monte Carlo runs give uncertainty ranges.

## Milestones

1. ✅ **Data foundation:** downloads, joined 1500-2025 history, quality labels, report
2. ✅ **History dashboard:** map, time series, share of world GDP, rankings (React + FastAPI)
3. **Model:** `gdpsim` calibrated and back-tested, SSP presets
4. **Levers:** global/group/country settings, lever paths, grid editor, bulk group edits
5. **Scenarios and analysis:** save, compare, diff, growth accounting, tornado charts, Monte Carlo ranges
6. **Self-review:** use it, fix what's awkward
7. **Public release:** read-only public mode, performance, accessibility, attributions
