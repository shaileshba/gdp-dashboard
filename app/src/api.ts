// Types and fetch helpers for the Python API (api/main.py).

export type Metric = 'gdp' | 'gdppc' | 'pop'
export type GroupingKey = 'maddison_region' | 'wb_region' | 'income_group'
export type Flag = 'observed' | 'interpolated' | 'extended' | 'parent' | 'regional'

export interface Country {
  iso3: string
  name: string
  maddison_region: string
  wb_region: string
  income_group: string
}

export interface Meta {
  first_year: number
  last_year: number
  measured_flags: Flag[]
  groupings: { key: GroupingKey; label: string; groups: string[] }[]
  countries: Country[]
}

export interface SnapshotRow {
  iso3: string
  name: string
  year: number
  gdp: number
  gdppc: number
  pop: number
  flag: Flag
  gdppc_flag: Flag
  pop_flag: Flag
  world_share: number
  gdppc_growth_10y: number | null
  rank_gdp: number
  rank_gdppc: number
  rank_pop: number
}

export interface SeriesPoint {
  year: number
  gdp: number
  gdppc: number
  pop: number
  flag: Flag
}

export interface WorldRow {
  year: number
  gdp: number
  pop: number
  gdppc: number
  measured_share: number
  countries_observed: number
}

export interface GroupRow {
  year: number
  grp: string
  gdp: number
  pop: number
}

const cache = new Map<string, Promise<unknown>>()

/** GET a JSON endpoint. Results are cached for the session (the data never changes while running). */
export function getJson<T>(path: string): Promise<T> {
  let p = cache.get(path)
  if (!p) {
    p = fetch(path).then(async (r) => {
      if (!r.ok) {
        const body = await r.json().catch(() => ({}))
        throw new Error(body.detail ?? `${r.status} ${r.statusText}`)
      }
      return r.json()
    })
    p.catch(() => cache.delete(path)) // let a failed request be retried
    cache.set(path, p)
  }
  return p as Promise<T>
}

export const isEstimate = (flag: Flag) => flag === 'parent' || flag === 'regional'

export const FLAG_LABEL: Record<Flag, string> = {
  observed: 'Observed',
  interpolated: 'Interpolated',
  extended: 'Extended (WB/UN growth)',
  parent: 'Estimate (former state)',
  regional: 'Estimate (regional growth)',
}
