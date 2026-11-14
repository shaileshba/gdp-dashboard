// Chart colours. Values come from the validated reference palette (dataviz skill, palette.md):
// categorical slots pass adjacent-pair colour-blind checks in both modes; the income ramp passes
// the ordinal checks. Charts need real colour strings (SVG attributes), so they live here as well
// as in index.css.

import { useEffect, useState } from 'react'

export type Mode = 'light' | 'dark'

export interface Palette {
  surface: string
  text1: string
  text2: string
  muted: string
  grid: string
  axis: string
  noData: string
  hatch: string
  series: string[] // 8 categorical slots, fixed order
  seq: string[] // 7 sequential steps, low -> high
  ordinal: string[] // 4 ordinal steps, low -> high (income groups)
  other: string // "Unclassified" group
}

const LIGHT: Palette = {
  surface: '#fcfcfb',
  text1: '#0b0b0b',
  text2: '#52514e',
  muted: '#898781',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  noData: '#e1e0d9',
  hatch: '#0b0b0b',
  series: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'],
  seq: ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'],
  ordinal: ['#86b6ef', '#3987e5', '#1c5cab', '#0d366b'],
  other: '#898781',
}

const DARK: Palette = {
  surface: '#1a1a19',
  text1: '#f0efec',
  text2: '#c3c2b7',
  muted: '#898781',
  grid: '#2c2c2a',
  axis: '#383835',
  noData: '#2c2c2a',
  hatch: '#f0efec',
  series: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#0ca30c', '#9085e9', '#e66767'],
  // On the dark surface, bigger values step *toward* the light end so they stand out.
  seq: ['#104281', '#184f95', '#256abf', '#3987e5', '#6da7ec', '#9ec5f4', '#cde2fb'],
  ordinal: ['#184f95', '#2a78d6', '#6da7ec', '#b7d3f6'],
  other: '#898781',
}

export const palettes: Record<Mode, Palette> = { light: LIGHT, dark: DARK }

const STORAGE_KEY = 'gdp-dashboard-theme'

function readStored(): Mode | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === 'light' || v === 'dark' ? v : null
  } catch {
    return null
  }
}

/** Light/dark mode: follows the OS until the user picks one, then remembers the choice. */
export function useTheme(): [Mode, (m: Mode) => void] {
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  const [chosen, setChosen] = useState<Mode | null>(readStored)
  const [osDark, setOsDark] = useState(media.matches)

  useEffect(() => {
    const onChange = (e: MediaQueryListEvent) => setOsDark(e.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [media])

  const mode: Mode = chosen ?? (osDark ? 'dark' : 'light')
  useEffect(() => {
    document.documentElement.dataset.theme = mode
  }, [mode])

  const set = (m: Mode) => {
    setChosen(m)
    try {
      localStorage.setItem(STORAGE_KEY, m)
    } catch {
      /* private window: the choice just isn't remembered */
    }
  }
  return [mode, set]
}

/** Colour for each group in a grouping. Order is fixed (from the API), so colours never shift. */
export function groupColors(groups: string[], ordinal: boolean, p: Palette): Record<string, string> {
  const out: Record<string, string> = {}
  const real = groups.filter((g) => g !== 'Unclassified')
  real.forEach((g, i) => {
    out[g] = ordinal ? p.ordinal[Math.min(i, p.ordinal.length - 1)] : p.series[i % p.series.length]
  })
  out['Unclassified'] = p.other
  return out
}
