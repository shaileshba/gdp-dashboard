import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { GroupRow } from '../api'
import { compact, pct } from '../format'
import type { Palette } from '../theme'

interface Props {
  measure: 'gdp' | 'pop'
  groupingLabel: string
  groups: string[]
  colors: Record<string, string>
  data: GroupRow[] | null
  loading: boolean
  year: number
  firstYear: number
  lastYear: number
  palette: Palette
  onYear: (year: number) => void
}

const TABLE_YEARS = [1500, 1700, 1820, 1870, 1913, 1950, 1980, 2000]

export function ShareChart(props: Props) {
  const { measure, groupingLabel, groups, colors, data, loading, year, firstYear, lastYear, palette, onYear } = props
  const [showTable, setShowTable] = useState(false)
  const what = measure === 'gdp' ? 'GDP' : 'population'

  // Rows of {year, <group>: share}. Shares are computed here so the tooltip and table agree.
  const rows = useMemo(() => {
    const byYear = new Map<number, Record<string, number>>()
    for (const r of data ?? []) {
      const row = byYear.get(r.year) ?? { year: r.year, _total: 0 }
      row[r.grp] = r[measure]
      row._total += r[measure]
      byYear.set(r.year, row)
    }
    const out = [...byYear.values()].sort((a, b) => a.year - b.year)
    for (const row of out) for (const g of groups) row[g] = (row[g] ?? 0) / row._total
    return out
  }, [data, groups, measure])
  const rowOf = useMemo(() => new Map(rows.map((r) => [r.year, r])), [rows])

  const TooltipBody = ({ active, label }: { active?: boolean; label?: string | number }) => {
    if (!active || label == null) return null
    const r = rowOf.get(Number(label))
    if (!r) return null
    return (
      <div className="tooltip static">
        <div className="tt-head">
          {label} · world {what} {measure === 'gdp' ? '$' : ''}
          {compact(r._total)}
        </div>
        {[...groups].reverse().map((g) => (
          <div className="tt-row" key={g}>
            <span className="rect-key" style={{ background: colors[g] }} />
            <span className="tt-value">{pct(r[g])}</span>
            <span className="tt-name">{g}</span>
          </div>
        ))}
      </div>
    )
  }

  const tableYears = [...TABLE_YEARS.filter((y) => y >= firstYear && y < lastYear), lastYear]

  return (
    <section className="card" aria-labelledby="share-title">
      <header className="card-head">
        <div>
          <h2 id="share-title">Share of world {what}</h2>
          <p className="sub">Grouped by {groupingLabel}. Before 1820 most of the world total is estimated.</p>
        </div>
        <div className="seg" role="group" aria-label="Chart options">
          <button aria-pressed={showTable} onClick={() => setShowTable(!showTable)}>
            Table
          </button>
        </div>
      </header>

      <ul className="legend" aria-label="Groups">
        {groups.map((g) => (
          <li key={g}>
            <span className="rect-key" style={{ background: colors[g] }} />
            {g}
          </li>
        ))}
      </ul>

      {showTable ? (
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th>{groupingLabel}</th>
                {tableYears.map((y) => (
                  <th key={y} className="num">
                    {y}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <tr key={g}>
                  <th scope="row">{g}</th>
                  {tableYears.map((y) => (
                    <td key={y} className="num">
                      {pct(rowOf.get(y)?.[g])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className={`chart${loading ? ' is-loading' : ''}`} style={{ height: 340 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={rows}
              margin={{ top: 8, right: 16, bottom: 0, left: 4 }}
              onClick={(s) => s?.activeLabel != null && onYear(Number(s.activeLabel))}
            >
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
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1]}
                tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                stroke={palette.axis}
                tick={{ fill: palette.muted, fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={44}
              />
              <Tooltip content={TooltipBody} cursor={{ stroke: palette.text1, strokeWidth: 1 }} isAnimationActive={false} />
              {groups.map((g) => (
                <Area
                  key={g}
                  dataKey={g}
                  stackId="share"
                  type="linear"
                  fill={colors[g]}
                  fillOpacity={0.88}
                  stroke={palette.surface}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                  activeDot={false}
                />
              ))}
              <ReferenceLine x={year} stroke={palette.text1} strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
