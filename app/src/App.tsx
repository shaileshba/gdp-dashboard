import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Country, GroupingKey, GroupRow, Meta, Metric, SeriesPoint, SnapshotRow, WorldRow } from './api'
import { Rankings } from './components/Rankings'
import { ShareChart } from './components/ShareChart'
import { StatTiles } from './components/StatTiles'
import { TimeSeries, type SelectedCountry } from './components/TimeSeries'
import { WorldMap } from './components/WorldMap'
import { METRICS } from './format'
import { groupColors, palettes, useTheme } from './theme'
import { useFetch } from './useFetch'

const MAX_SELECTED = 8 // one per categorical colour slot
const DEFAULT_SELECTED = ['CHN', 'IND', 'GBR', 'USA']

export default function App() {
  const meta = useFetch<Meta>('/api/meta')
  if (meta.error) return <ErrorPage message={meta.error} />
  if (!meta.data) return <div className="boot">Loading…</div>
  return <Dashboard meta={meta.data} />
}

function ErrorPage({ message }: { message: string }) {
  return (
    <main className="boot">
      <h1>Couldn't reach the data server</h1>
      <p>{message}</p>
      <p>
        Start it from the project folder with <code>uv run python -m api</code>, then reload this page.
      </p>
    </main>
  )
}

function Dashboard({ meta }: { meta: Meta }) {
  const [mode, setMode] = useTheme()
  const palette = palettes[mode]

  // The view is kept in the address bar (?year=1820&metric=gdp&group=income_group&c=CHN,IND)
  // so it can be bookmarked or shared.
  const [initial] = useState(() => new URLSearchParams(window.location.search))
  const [metric, setMetric] = useState<Metric>(() => {
    const m = initial.get('metric')
    return METRICS.some((x) => x.key === m) ? (m as Metric) : 'gdppc'
  })
  const [year, setYear] = useState(() => {
    const y = Number(initial.get('year'))
    return Number.isInteger(y) && y >= meta.first_year && y <= meta.last_year ? y : meta.last_year
  })
  const [grouping, setGrouping] = useState<GroupingKey>(() => {
    const g = initial.get('group')
    return meta.groupings.some((x) => x.key === g) ? (g as GroupingKey) : 'maddison_region'
  })
  const [markEstimates, setMarkEstimates] = useState(true)
  const [playing, setPlaying] = useState(false)
  const [selected, setSelected] = useState<SelectedCountry[]>(() => {
    const names = new Map(meta.countries.map((c) => [c.iso3, c.name]))
    const fromUrl = initial.get('c')?.toUpperCase().split(',')
    const codes = [...new Set(fromUrl ?? DEFAULT_SELECTED)].filter((c) => names.has(c)).slice(0, MAX_SELECTED)
    return codes.map((iso3, slot) => ({ iso3, name: names.get(iso3)!, slot }))
  })

  useEffect(() => {
    const q = new URLSearchParams({ year: String(year), metric, group: grouping })
    q.set('c', selected.map((s) => s.iso3).join(','))
    window.history.replaceState(null, '', `?${q.toString().replace(/%2C/g, ',')}`)
  }, [year, metric, grouping, selected])

  const countries = useMemo(() => new Map<string, Country>(meta.countries.map((c) => [c.iso3, c])), [meta])
  const groupingInfo = meta.groupings.find((g) => g.key === grouping)!
  const colors = useMemo(
    () => groupColors(groupingInfo.groups, grouping === 'income_group', palette),
    [groupingInfo, grouping, palette],
  )

  const snapshot = useFetch<SnapshotRow[]>(`/api/snapshot?year=${year}`)
  const world = useFetch<WorldRow[]>('/api/world')
  const groups = useFetch<GroupRow[]>(`/api/groups?by=${grouping}`)
  const seriesPath = selected.length ? `/api/series?iso3=${selected.map((s) => s.iso3).sort().join(',')}` : null
  const series = useFetch<Record<string, SeriesPoint[]>>(seriesPath)

  const toggle = useCallback(
    (iso3: string) =>
      setSelected((sel) => {
        if (sel.some((s) => s.iso3 === iso3)) return sel.filter((s) => s.iso3 !== iso3)
        if (sel.length >= MAX_SELECTED) return sel
        // Take the first free colour slot, so countries already shown keep their colour.
        const used = new Set(sel.map((s) => s.slot))
        const slot = [...Array(MAX_SELECTED).keys()].find((i) => !used.has(i))!
        return [...sel, { iso3, name: countries.get(iso3)?.name ?? iso3, slot }]
      }),
    [countries],
  )

  // Play: step through the years, a few per tick, and stop at the end.
  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => {
      setYear((y) => Math.min(meta.last_year, y + (y < 1820 ? 10 : 2)))
    }, 120)
    return () => window.clearInterval(id)
  }, [playing, meta.last_year])
  if (playing && year >= meta.last_year) setPlaying(false) // reached the end

  const play = () => {
    if (!playing && year >= meta.last_year) setYear(meta.first_year)
    setPlaying(!playing)
  }

  const selectedIso = selected.map((s) => s.iso3)

  return (
    <div className="page">
      <header className="top">
        <div>
          <h1>World GDP, {meta.first_year}–{meta.last_year}</h1>
          <p className="sub">
            {meta.countries.length} economies within present-day borders. Maddison Project 2023, extended with World
            Bank and UN data.
          </p>
        </div>
        <div className="seg" role="group" aria-label="Colour theme">
          <button aria-pressed={mode === 'light'} onClick={() => setMode('light')}>
            Light
          </button>
          <button aria-pressed={mode === 'dark'} onClick={() => setMode('dark')}>
            Dark
          </button>
        </div>
      </header>

      <div className="filters" role="toolbar" aria-label="Filters">
        <div className="field year-field">
          <label htmlFor="year">Year</label>
          <div className="year-row">
            <button className="play" onClick={play} aria-label={playing ? 'Pause' : 'Play through the years'}>
              {playing ? '❚❚' : '▶'}
            </button>
            <input
              id="year"
              type="range"
              min={meta.first_year}
              max={meta.last_year}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
            <input
              type="number"
              className="year-num"
              min={meta.first_year}
              max={meta.last_year}
              value={year}
              aria-label="Year"
              onChange={(e) => {
                const v = Number(e.target.value)
                if (v >= meta.first_year && v <= meta.last_year) setYear(v)
              }}
            />
          </div>
        </div>
        <div className="field">
          <span className="field-label" id="metric-label">
            Measure
          </span>
          <div className="seg" role="group" aria-labelledby="metric-label">
            {METRICS.map((m) => (
              <button key={m.key} aria-pressed={metric === m.key} onClick={() => setMetric(m.key)}>
                {m.label}
              </button>
            ))}
          </div>
        </div>
        <div className="field">
          <label htmlFor="grouping">Group by</label>
          <select id="grouping" value={grouping} onChange={(e) => setGrouping(e.target.value as GroupingKey)}>
            {meta.groupings.map((g) => (
              <option key={g.key} value={g.key}>
                {g.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="add">Compare</label>
          <select
            id="add"
            value=""
            disabled={selected.length >= MAX_SELECTED}
            onChange={(e) => e.target.value && toggle(e.target.value)}
          >
            <option value="">
              {selected.length >= MAX_SELECTED ? 'Chart is full (8)' : 'Add a country…'}
            </option>
            {meta.countries
              .filter((c) => !selectedIso.includes(c.iso3))
              .map((c) => (
                <option key={c.iso3} value={c.iso3}>
                  {c.name}
                </option>
              ))}
          </select>
        </div>
        <label className="check">
          <input type="checkbox" checked={markEstimates} onChange={(e) => setMarkEstimates(e.target.checked)} />
          Hatch estimates on map
        </label>
      </div>

      <StatTiles year={year} world={world.data} />

      {snapshot.error && <p className="error">Couldn't load {year}: {snapshot.error}</p>}

      <WorldMap
        metric={metric}
        year={year}
        rows={snapshot.data}
        loading={snapshot.loading}
        palette={palette}
        selected={selectedIso}
        onToggle={toggle}
        markEstimates={markEstimates}
      />

      <div className="two-col">
        <TimeSeries
          metric={metric}
          year={year}
          firstYear={meta.first_year}
          lastYear={meta.last_year}
          selected={selected}
          series={series.data}
          loading={series.loading}
          palette={palette}
          onRemove={toggle}
          onYear={setYear}
        />
        <ShareChart
          measure={metric === 'pop' ? 'pop' : 'gdp'}
          groupingLabel={groupingInfo.label}
          groups={groupingInfo.groups}
          colors={colors}
          data={groups.data}
          loading={groups.loading}
          year={year}
          firstYear={meta.first_year}
          lastYear={meta.last_year}
          palette={palette}
          onYear={setYear}
        />
      </div>

      <Rankings
        metric={metric}
        year={year}
        rows={snapshot.data}
        loading={snapshot.loading}
        countries={countries}
        grouping={grouping}
        groupingLabel={groupingInfo.label}
        groupColors={colors}
        palette={palette}
        selected={selectedIso}
        onToggle={toggle}
        canAdd={selected.length < MAX_SELECTED}
      />

      <footer className="foot">
        Values in 2011 international dollars (PPP). Sources: Maddison Project Database 2023, World Bank WDI, UN World
        Population Prospects 2024 (CC BY). Estimates before a country's first observation borrow growth from its region
        or former state; see the data quality report.
      </footer>
    </div>
  )
}
