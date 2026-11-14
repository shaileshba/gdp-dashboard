import { useMemo, useState } from 'react'
import { FLAG_LABEL, isEstimate, type Country, type GroupingKey, type Metric, type SnapshotRow } from '../api'
import { formatMetric, metricInfo, pct, signedPct } from '../format'
import type { Palette } from '../theme'

type SortKey = 'value' | 'share' | 'growth' | 'name'

interface Props {
  metric: Metric
  year: number
  rows: SnapshotRow[] | null
  loading: boolean
  countries: Map<string, Country>
  grouping: GroupingKey
  groupingLabel: string
  groupColors: Record<string, string>
  palette: Palette
  selected: string[]
  onToggle: (iso3: string) => void
  canAdd: boolean
}

export function Rankings(props: Props) {
  const { metric, year, rows, loading, countries, grouping, groupingLabel, groupColors, palette, selected, onToggle, canAdd } =
    props
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'value', desc: true })
  const [showAll, setShowAll] = useState(false)
  const [query, setQuery] = useState('')
  const info = metricInfo(metric)

  const sorted = useMemo(() => {
    const val = (r: SnapshotRow): number | string => {
      if (sort.key === 'value') return r[metric]
      if (sort.key === 'share') return r.world_share
      if (sort.key === 'growth') return r.gdppc_growth_10y ?? -Infinity
      return r.name
    }
    const q = query.trim().toLowerCase()
    return [...(rows ?? [])]
      .filter((r) => !q || r.name.toLowerCase().includes(q) || r.iso3.toLowerCase() === q)
      .sort((a, b) => {
        const va = val(a)
        const vb = val(b)
        const c = typeof va === 'string' ? va.localeCompare(vb as string) : va - (vb as number)
        return sort.desc ? -c : c
      })
  }, [rows, metric, sort, query])

  const shown = showAll || query ? sorted : sorted.slice(0, 20)
  const max = Math.max(...(rows ?? []).map((r) => r[metric]), 1)

  const header = (key: SortKey, label: string, num = true) => (
    <th className={num ? 'num' : undefined} aria-sort={sort.key === key ? (sort.desc ? 'descending' : 'ascending') : 'none'}>
      <button
        className="sort"
        onClick={() => setSort((s) => ({ key, desc: s.key === key ? !s.desc : key !== 'name' }))}
      >
        {label}
        <span aria-hidden className="sort-arrow">
          {sort.key === key ? (sort.desc ? '▼' : '▲') : ''}
        </span>
      </button>
    </th>
  )

  return (
    <section className="card" aria-labelledby="rank-title">
      <header className="card-head">
        <div>
          <h2 id="rank-title">
            {info.label} rankings, {year}
          </h2>
          <p className="sub">
            {rows?.length ?? 0} countries. Click a row to add or remove it from the comparison chart. Growth is GDP per
            person, average per year over the previous 10 years.
          </p>
        </div>
        <input
          type="search"
          className="search"
          placeholder="Find a country…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Filter countries"
        />
      </header>

      <div className={`table-scroll${loading ? ' is-loading' : ''}`}>
        <table className="data rankings">
          <thead>
            <tr>
              <th className="num">#</th>
              {header('name', 'Country', false)}
              <th>{groupingLabel}</th>
              {header('value', info.label)}
              <th className="bar-col" aria-hidden />
              {header('share', 'Share of world GDP')}
              {header('growth', 'Growth (10y)')}
              <th>Data</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const isSel = selected.includes(r.iso3)
              const grp = countries.get(r.iso3)?.[grouping] ?? ''
              return (
                <tr
                  key={r.iso3}
                  className={isSel ? 'selected' : undefined}
                  onClick={() => (isSel || canAdd) && onToggle(r.iso3)}
                >
                  <td className="num muted">{r[`rank_${metric}`]}</td>
                  <th scope="row">
                    <button
                      className="row-btn"
                      aria-pressed={isSel}
                      disabled={!isSel && !canAdd}
                      title={!isSel && !canAdd ? 'The comparison chart holds 8 countries' : undefined}
                      onClick={(e) => {
                        e.stopPropagation()
                        onToggle(r.iso3)
                      }}
                    >
                      {r.name}
                    </button>
                  </th>
                  <td className="grp">
                    <span className="rect-key" style={{ background: groupColors[grp] }} />
                    {grp}
                  </td>
                  <td className={`num${isEstimate(r.flag) ? ' est' : ''}`}>{formatMetric(metric, r[metric])}</td>
                  <td className="bar-col" aria-hidden>
                    <span className="bar" style={{ width: `${(r[metric] / max) * 100}%`, background: palette.series[0] }} />
                  </td>
                  <td className="num">{pct(r.world_share, r.world_share < 0.001 ? 2 : 1)}</td>
                  <td className="num">{signedPct(r.gdppc_growth_10y)}</td>
                  <td className="muted flag">{FLAG_LABEL[r.flag]}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {!query && sorted.length > 20 && (
        <button className="link" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Show top 20' : `Show all ${sorted.length}`}
        </button>
      )}
    </section>
  )
}
