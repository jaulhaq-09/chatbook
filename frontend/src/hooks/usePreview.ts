import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { Preview, RenderOptions } from '../api/types'

export interface PreviewState {
  data: Preview | null
  loading: boolean
  error: string | null
}

const DEBOUNCE_MS = 350

/**
 * Fetches the on-screen preview whenever the options, volume or page change.
 * Calls are debounced and a newer request cancels the one before it, so dragging a
 * control never queues a pile of renders on the server.
 */
export function usePreview(jobId: string | null, options: RenderOptions, volume: number, page: number): PreviewState {
  const [state, setState] = useState<PreviewState>({ data: null, loading: false, error: null })
  const key = JSON.stringify(options)

  useEffect(() => {
    if (!jobId) {
      setState({ data: null, loading: false, error: null })
      return
    }
    const controller = new AbortController()
    setState((s) => ({ ...s, loading: true, error: null }))
    const timer = window.setTimeout(async () => {
      try {
        const data = await api.preview(jobId, options, volume, page, controller.signal)
        setState({ data, loading: false, error: null })
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof ApiError ? err.message : 'The preview could not be created.',
        }))
      }
    }, DEBOUNCE_MS)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
    // `key` stands in for `options` so a new object with equal content does not refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, key, volume, page])

  return state
}
