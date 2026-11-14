import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { RenderOptions } from '../api/types'

export interface PdfState {
  data: ArrayBuffer | null
  loading: boolean
  error: string | null
}

const DEBOUNCE_MS = 450

/**
 * The printed pages of the section being previewed. The previous pages stay on screen while new ones are
 * made, so changing a setting never flashes an empty view.
 */
export function usePreviewPdf(
  jobId: string | null,
  options: RenderOptions,
  volume: number,
  page: number,
  backgroundVersion = '',
): PdfState {
  const [state, setState] = useState<PdfState>({ data: null, loading: false, error: null })
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
        const data = await api.previewPdf(jobId, options, volume, page, controller.signal)
        setState({ data, loading: false, error: null })
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        // "Nothing matches" is shown by the stage; any other failure keeps the old pages and says why.
        const message = err instanceof ApiError ? err.message : 'The preview pages could not be made.'
        setState((s) => ({ data: err instanceof ApiError && err.status === 422 ? null : s.data, loading: false, error: message }))
      }
    }, DEBOUNCE_MS)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
    // `key` stands in for `options` so an equal copy does not refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, key, volume, page, backgroundVersion])

  return state
}