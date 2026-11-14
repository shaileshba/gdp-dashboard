import { useEffect, useState } from 'react'
import { getJson } from './api'

/**
 * Fetch JSON and keep the previous result while the next one loads, so charts hold their frame
 * (shown dimmed via `loading`) instead of flashing empty.
 */
export function useFetch<T>(path: string | null): { data: T | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (path === null) return
    let live = true
    setLoading(true)
    getJson<T>(path)
      .then((d) => {
        if (!live) return
        setData(d)
        setError(null)
      })
      .catch((e: Error) => live && setError(e.message))
      .finally(() => live && setLoading(false))
    return () => {
      live = false
    }
  }, [path])

  return { data, loading, error }
}
