import { geoEqualEarth, geoPath } from 'd3-geo'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import countriesLib from 'i18n-iso-countries'
import { useMemo, useState } from 'react'
import { feature } from 'topojson-client'
import type { GeometryCollection, Topology } from 'topojson-specification'
import worldTopo from 'world-atlas/countries-50m.json'
import { FLAG_LABEL, isEstimate, type Metric, type SnapshotRow } from '../api'
import { formatMetric, metricInfo, pct } from '../format'
import type { Palette } from '../theme'

const WIDTH = 960
const HEIGHT = 470

// Fixed class breaks per metric, the same in every year, so playing through time shows real change.
const BREAKS: Record<Metric, number[]> = {
  gdppc: [1000, 2000, 4000, 8000, 16000, 32000],
  gdp: [1e10, 3e10, 1e11, 3e11, 1e12, 3e12],
  pop: [1e6, 3e6, 1e7, 3e7, 1e8, 3e8],
}

const topo = worldTopo as unknown as Topology<{ countries: GeometryCollection<{ name: string }> }>
const world = feature(topo, topo.objects.countries) as FeatureCollection<Geometry, { name: string }>
const shapes = world.features
  .filter((f) => f.properties.name !== 'Antarctica')
  .map((f) => ({ f, iso3: countriesLib.numericToAlpha3(String(f.id ?? '')) ?? null }))

const projection = geoEqualEarth().fitExtent(
  [
    [4, 4],
    [WIDTH - 4, HEIGHT - 4],
  ],
  { type: 'FeatureCollection', features: shapes.map((s) => s.f) } as FeatureCollection,
)
const pathGen = geoPath(projection)
const paths = shapes.map((s) => ({ ...s, d: pathGen(s.f as Feature) ?? '' }))

function classOf(m: Metric, v: number): number {
  const b = BREAKS[m]
  let i = 0
  while (i < b.length && v >= b[i]) i++
  return i
}

interface Props {
  metric: Metric
  year: number
  rows: SnapshotRow[] | null
  loading: boolean
  palette: Palette
  selected: string[]
  onToggle: (iso3: string) => void
  markEstimates: boolean
}

export function WorldMap({ metric, year, rows, loading, palette, selected, onToggle, markEstimates }: Props) {
  const [hover, setHover] = useState<{ iso3: string | null; name: string; x: number; y: number } | null>(null)
  const byIso = useMemo(() => new Map((rows ?? []).map((r) => [r.iso3, r])), [rows])
  const info = metricInfo(metric)
  const breaks = BREAKS[metric]
  const hovered = hover?.iso3 ? byIso.get(hover.iso3) : undefined

  const legend = palette.seq.map((c, i) => ({
    color: c,
    label:
      i === 0
        ? `< ${formatMetric(metric, breaks[0])}`
        : i === breaks.length
          ? `≥ ${formatMetric(metric, breaks[i - 1])}`
          : `${formatMetric(metric, breaks[i - 1])}–${formatMetric(metric, breaks[i])}`,
  }))

  return (
    <section className="card map-card" aria-labelledby="map-title">
      <header className="card-head">
        <div>
          <h2 id="map-title">
            {info.label}, {year}
          </h2>
          <p className="sub">
            {info.unit}, present-day borders. Click a country to add it to the comparison chart.
          </p>
        </div>
      </header>

      <div className={`map-wrap${loading ? ' is-loading' : ''}`} onMouseLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`World map of ${info.label} in ${year}`}>
          <defs>
            <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke={palette.hatch} strokeWidth="1.2" strokeOpacity="0.45" />
            </pattern>
          </defs>
          {paths.map(({ iso3, d, f }, i) => {
            const row = iso3 ? byIso.get(iso3) : undefined
            const fill = row ? palette.seq[classOf(metric, row[metric])] : palette.noData
            const isSel = !!iso3 && selected.includes(iso3)
            return (
              <g key={i}>
                <path
                  d={d}
                  fill={fill}
                  stroke={palette.surface}
                  strokeWidth={0.5}
                  className={row ? 'country has-data' : 'country'}
                  onMouseMove={(e) => {
                    const box = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect()
                    setHover({ iso3, name: f.properties.name, x: e.clientX - box.left, y: e.clientY - box.top })
                  }}
                  onClick={() => row && onToggle(row.iso3)}
                />
                {row && markEstimates && isEstimate(row.flag) && (
                  <path d={d} fill="url(#hatch)" pointerEvents="none" />
                )}
                {isSel && <path d={d} fill="none" stroke={palette.text1} strokeWidth={1.5} pointerEvents="none" />}
              </g>
            )
          })}
        </svg>

        {hover && (
          <div className="tooltip" style={{ left: hover.x, top: hover.y }} role="status">
            {hovered ? (
              <>
                <div className="tt-value">{formatMetric(metric, hovered[metric])}</div>
                <div className="tt-name">{hovered.name}</div>
                <div className="tt-meta">
                  #{hovered[`rank_${metric}`]} of {rows?.length} · {pct(hovered.world_share)} of world GDP
                </div>
                <div className="tt-meta">{FLAG_LABEL[hovered.flag]}</div>
              </>
            ) : (
              <>
                <div className="tt-name">{hover.name}</div>
                <div className="tt-meta">No data</div>
              </>
            )}
          </div>
        )}
      </div>

      <ul className="map-legend" aria-label="Map colour key">
        {legend.map((l) => (
          <li key={l.label}>
            <span className="swatch" style={{ background: l.color }} />
            {l.label}
          </li>
        ))}
        <li>
          <span className="swatch" style={{ background: palette.noData }} />
          No data
        </li>
        {markEstimates && (
          <li>
            <svg className="swatch" viewBox="0 0 14 14" aria-hidden>
              <rect width="14" height="14" fill={palette.seq[2]} />
              <rect width="14" height="14" fill="url(#hatch)" />
            </svg>
            Estimate (borrowed growth)
          </li>
        )}
      </ul>
    </section>
  )
}
