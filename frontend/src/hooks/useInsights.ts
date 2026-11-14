import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { Insights } from '../api/types'

export interface InsightsState {
  data: Insights | null
  loading: boolean
  error: string | null
}

/** Loads the chat statistics once per chat, and only when the Insights tab is open. */
export function useInsights(jobId: string | null, enabled: boolean): InsightsState {
  const [state, setState] = useState<InsightsState>({ data: null, loading: false, error: null })

  // A different chat (or a merge) invalidates what was loaded.
  useEffect(() => {
    setState({ data: null, loading: false, error: null })
  }, [jobId])

  const have = state.data !== null
  useEffect(() => {
    if (!jobId || !enabled || have) return
    const controller = new AbortController()
    setState((s) => ({ ...s, loading: true, error: null }))
    api
      .insights(jobId, controller.signal)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setState({ data: null, loading: false, error: err instanceof ApiError ? err.message : 'Could not load insights.' })
      })
    return () => controller.abort()
  }, [jobId, enabled, have])

  return state
}