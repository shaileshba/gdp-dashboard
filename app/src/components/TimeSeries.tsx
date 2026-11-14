import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { FLAG_LABEL, isEstimate, type Metric, type SeriesPoint } from '../api'
import { formatMetric, metricInfo, tickMetric } from '../format'
import type { Palette } from '../theme'

export interface SelectedCountry {
  iso3: string
  name: string
  slot: number // categorical colour slot, kept for as long as the country stays selected
}

interface Props {
  metric: Metric
  year: number
  firstYear: number
  lastYear: number
  selected: SelectedCountry[]
  series: Record<string, SeriesPoint[]> | null
  loading: boolean
  palette: Palette
  onRemove: (iso3: string) => void
  onYear: (year: number) => void
}

const TABLE_YEARS = [1500, 1600, 1700, 1820, 1870, 1913, 1950, 1973, 2000]

export function TimeSeries(props: Props) {
  const { metric, year, firstYear, lastYear, selected, series, loading, palette, onRemove, onYear } = props
  const [log, setLog] = useState(true)
  const [showTable, setShowTable] = useState(false)
  const info = metricInfo(metric)

  // Each country becomes two series: its own data (solid) and borrowed-growth estimates (dashed).
  // The point where they meet is in both, so the line has no gap.
  const { rows, lookup } = useMemo(() => {
    const lookup = new Map<string, Map<number, SeriesPoint>>()
    const byYear = new Map<number, Record<string, number | null>>()
    for (const c of selected) {
      const pts = series?.[c.iso3]
      if (!pts) continue
      lookup.set(c.iso3, new Map(pts.map((p) => [p.year, p])))
      pts.forEach((p, i) => {
        const row = byYear.get(p.year) ?? { year: p.year }
        const est = isEstimate(p.flag)
        const nextEst = i + 1 < pts.length && isEstimate(pts[i + 1].flag)
        const prevEst = i > 0 && isEstimate(pts[i - 1].flag)
        row[`${c.iso3}_m`] = !est ? p[metric] : null
        row[`${c.iso3}_e`] = est || nextEst || prevEst ? p[metric] : null
        byYear.set(p.year, row)
      })
    }
    return { rows: [...byYear.values()].sort((a, b) => a.year! - b.year!), lookup }
  }, [selected, series, metric])

  const directLabels = selected.length <= 4

  // Log axis: clean 1-2-5 ticks spanning the data, and a domain snapped to the outer ticks.
  const { logDomain, logTicks } = useMemo(() => {
    let lo = Infinity
    let hi = 0
    for (const pts of Object.values(series ?? {}))
      for (const p of pts) {
        lo = Math.min(lo, p[metric])
        hi = Math.max(hi, p[metric])
      }
    if (!(hi > 0)) return { logDomain: [1, 10] as [number, number], logTicks: [1, 10] }
    const all: number[] = []
    for (let e = Math.floor(Math.log10(lo)) - 1; e <= Math.ceil(Math.log10(hi)) + 1; e++)
      for (const m of [1, 2, 5]) all.push(m * 10 ** e)
    const below = all.filter((t) => t <= lo).pop() ?? lo
    const above = all.find((t) => t >= hi) ?? hi
    let ticks = all.filter((t) => t >= below && t <= above)
    if (ticks.length > 9) ticks = ticks.filter((t) => /^1/.test(String(t))) // powers of ten only
    return { logDomain: [below, above] as [number, number], logTicks: ticks }
  }, [series, metric])

  const TooltipBody = ({ active, label }: { active?: boolean; label?: string | number }) => {
    if (!active || label == null) return null
    const y = Number(label)
    const items = selected
      .map((c) => ({ c, p: lookup.get(c.iso3)?.get(y) }))
      .filter((x) => x.p)
      .sort((a, b) => b.p![metric] - a.p![metric])
    return (
      <div className="tooltip static">
        <div className="tt-head">{y}</div>
        {items.map(({ c, p }) => (
          <div className="tt-row" key={c.iso3}>
            <span className="line-key" style={{ background: palette.series[c.slot] }} />
            <span className="tt-value">{formatMetric(metric, p![metric])}</span>
            <span className="tt-name">
              {c.name}
              {isEstimate(p!.flag) && <em> · {FLAG_LABEL[p!.flag].toLowerCase()}</em>}
            </span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <section className="card" aria-labelledby="ts-title">
      <header className="card-head">
        <div>
          <h2 id="ts-title">{info.label} over time</h2>
          <p className="sub">
            {info.unit}. Dashed = estimated from regional or former-state growth. Click the chart to jump to a year.
          </p>
        </div>
        <div className="seg" role="group" aria-label="Chart options">
          <button aria-pressed={log} onClick={() => setLog(!log)}>
            Log scale
          </button>
          <button aria-pressed={showTable} onClick={() => setShowTable(!showTable)}>
            Table
          </button>
        </div>
      </header>

      <ul className="legend chips" aria-label="Countries in this chart">
        {selected.map((c) => (
          <li key={c.iso3}>
            <span className="line-key" style={{ background: palette.series[c.slot] }} />
            {c.name}
            <button className="chip-x" onClick={() => onRemove(c.iso3)} aria-label={`Remove ${c.name}`}>
              ×
            </button>
          </li>
        ))}
        {selected.length === 0 && <li className="muted">Pick countries on the map, in the rankings, or with search.</li>}
      </ul>

      {showTable ? (
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th>Country</th>
                {[...TABLE_YEARS.filter((y) => y >= firstYear && y < lastYear), lastYear].map((y) => (
                  <th key={y} className="num">
                    {y}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {selected.map((c) => (
                <tr key={c.iso3}>
                  <th scope="row">{c.name}</th>
                  {[...TABLE_YEARS.filter((y) => y >= firstYear && y < lastYear), lastYear].map((y) => {
                    const p = lookup.get(c.iso3)?.get(y)
                    return (
                      <td key={y} className={`num${p && isEstimate(p.flag) ? ' est' : ''}`}>
                        {p ? formatMetric(metric, p[metric]) : '–'}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="sub">Values in italics are estimates.</p>
        </div>
      ) : (
        <div className={`chart${loading ? ' is-loading' : ''}`} style={{ height: 340 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={rows}
              margin={{ top: 8, right: directLabels ? 104 : 16, bottom: 0, left: 4 }}
              onClick={(s) => s?.activeLabel != null && onYear(Number(s.activeLabel))}
            >
              <CartesianGrid stroke={palette.grid} vertical={false} />
              <XAxis
                dataKey="year"
                type="number"
                domain={[firstYear, lastYear]}
                ticks={[1500, 1600, 1700, 1800, 1900, 2000].filter((t) => t >= firstYear)}
                stroke={palette.axis}
                tick={{ fill: palette.muted, fontSize: 12 }}
                tickLine={false}
              />
              <YAxis
                scale={log ? 'log' : 'linear'}
                domain={log ? logDomain : [0, 'auto']}
                ticks={log ? logTicks : undefined}
                allowDataOverflow={false}
                tickFormatter={(v: number) => tickMetric(metric, v)}
                stroke={palette.axis}
                tick={{ fill: palette.muted, fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <ReferenceLine x={year} stroke={palette.text2} strokeWidth={1} />
              <Tooltip
                content={TooltipBody}
                cursor={{ stroke: palette.muted, strokeWidth: 1 }}
                isAnimationActive={false}
              />
              {selected.flatMap((c) => [
                <Line
                  key={`${c.iso3}_e`}
                  dataKey={`${c.iso3}_e`}
                  stroke={palette.series[c.slot]}
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  strokeOpacity={0.8}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                  connectNulls={false}
                />,
                <Line
                  key={`${c.iso3}_m`}
                  dataKey={`${c.iso3}_m`}
                  stroke={palette.series[c.slot]}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  dot={false}
                  activeDot={{ r: 4, stroke: palette.surface, strokeWidth: 2 }}
                  isAnimationActive={false}
                  connectNulls={false}
                  label={
                    directLabels
                      ? (lp: { x?: number | string; y?: number | string; index?: number }) =>
                          lp.index === rows.length - 1 ? (
                            <text
                              x={Number(lp.x) + 8}
                              y={Number(lp.y)}
                              dy={4}
                              fontSize={12}
                              fill={palette.text2}
                              key={c.iso3}
                            >
                              {c.name.length > 14 ? `${c.name.slice(0, 13)}…` : c.name}
                            </text>
                          ) : (
                            <g key={`${c.iso3}-${lp.index}`} />
                          )
                      : false
                  }
                />,
              ])}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
