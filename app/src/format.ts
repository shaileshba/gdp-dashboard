import type { Metric } from './api'

export const METRICS: { key: Metric; label: string; short: string; unit: string }[] = [
  { key: 'gdp', label: 'GDP', short: 'GDP', unit: '2011 int. $ (PPP)' },
  { key: 'gdppc', label: 'GDP per person', short: 'GDP/person', unit: '2011 int. $ (PPP)' },
  { key: 'pop', label: 'Population', short: 'Population', unit: 'people' },
]
export const metricInfo = (m: Metric) => METRICS.find((x) => x.key === m)!

const UNITS: [number, string][] = [
  [1e12, 'T'],
  [1e9, 'B'],
  [1e6, 'M'],
  [1e3, 'K'],
]

/** 1234 -> "1.2K", 3.4e12 -> "3.4T". Values under 10,000 are written in full. */
export function compact(v: number, digits = 1): string {
  if (!Number.isFinite(v)) return '–'
  const a = Math.abs(v)
  if (a < 1e4) return Math.round(v).toLocaleString('en-US')
  for (const [size, suffix] of UNITS) {
    if (a >= size) {
      const n = v / size
      return `${n >= 100 ? Math.round(n) : n.toFixed(digits).replace(/\.0$/, '')}${suffix}`
    }
  }
  return String(v)
}

export function formatMetric(m: Metric, v: number): string {
  if (m === 'pop') return compact(v)
  if (m === 'gdppc') return `$${Math.round(v).toLocaleString('en-US')}`
  return `$${compact(v)}`
}

/** Short axis tick for a metric. */
export function tickMetric(m: Metric, v: number): string {
  return m === 'pop' ? compact(v, 0) : `$${compact(v, 0)}`
}

export const pct = (v: number | null | undefined, digits = 1) =>
  v == null || !Number.isFinite(v) ? '–' : `${(v * 100).toFixed(digits)}%`

export const signedPct = (v: number | null | undefined, digits = 1) =>
  v == null || !Number.isFinite(v) ? '–' : `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(digits)}%`
