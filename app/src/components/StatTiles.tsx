import type { WorldRow } from '../api'
import { compact, pct, signedPct } from '../format'

interface Props {
  year: number
  world: WorldRow[] | null
}

function growth(now: number, past: number | undefined, years: number) {
  return past && years > 0 ? (now / past) ** (1 / years) - 1 : null
}

function Delta({ v, span }: { v: number | null; span: number }) {
  if (v == null) return <div className="delta muted">No earlier year to compare</div>
  const up = v >= 0
  return (
    <div className={`delta ${up ? 'up' : 'down'}`}>
      <span aria-hidden>{up ? '▲' : '▼'}</span> {signedPct(v, 2)} a year
      <span className="muted"> over the previous {span} years</span>
    </div>
  )
}

export function StatTiles({ year, world }: Props) {
  const byYear = new Map((world ?? []).map((w) => [w.year, w]))
  const now = byYear.get(year)
  if (!now) return <div className="tiles" />
  const first = world![0].year
  const pastYear = Math.max(first, year - 10)
  const past = byYear.get(pastYear)
  const span = year - pastYear

  return (
    <div className="tiles">
      <div className="tile hero">
        <div className="label">World GDP, {year}</div>
        <div className="value">${compact(now.gdp)}</div>
        <Delta v={growth(now.gdp, past?.gdp, span)} span={span} />
      </div>
      <div className="tile">
        <div className="label">World population</div>
        <div className="value">{compact(now.pop, 2)}</div>
        <Delta v={growth(now.pop, past?.pop, span)} span={span} />
      </div>
      <div className="tile">
        <div className="label">World GDP per person</div>
        <div className="value">${Math.round(now.gdppc).toLocaleString('en-US')}</div>
        <Delta v={growth(now.gdppc, past?.gdppc, span)} span={span} />
      </div>
      <div className="tile">
        <div className="label">World GDP resting on countries' own data</div>
        <div className="value">{pct(now.measured_share, 0)}</div>
        <div className="delta muted">
          {now.countries_observed > 0
            ? `${now.countries_observed} countries with an observed GDP per person this year`
            : 'After 2022: Maddison figures rolled forward with World Bank and UN growth'}
        </div>
      </div>
    </div>
  )
}
