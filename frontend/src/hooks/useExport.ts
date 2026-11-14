import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { ExportJob, RenderOptions } from '../api/types'

const POLL_MS = 700

export interface ExportController {
  current: ExportJob | null
  busy: boolean
  error: string | null
  start: (options: RenderOptions) => Promise<void>
  cancel: () => Promise<void>
  dismiss: () => void
}

/** Starts a PDF export and follows it until it finishes, fails or is cancelled. */
export function useExport(jobId: string | null): ExportController {
  const [current, setCurrent] = useState<ExportJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const currentRef = useRef<ExportJob | null>(null)
  currentRef.current = current

  // A different chat means any earlier export no longer applies.
  useEffect(() => {
    setCurrent(null)
    setError(null)
  }, [jobId])

  const active = current && (current.status === 'queued' || current.status === 'running')
  const exportId = current?.id

  useEffect(() => {
    if (!active || !jobId || !exportId) return
    let stopped = false
    const timer = window.setInterval(async () => {
      try {
        const next = await api.getExport(jobId, exportId)
        if (!stopped) setCurrent(next)
      } catch (err) {
        if (stopped) return
        setError(err instanceof ApiError ? err.message : 'Lost contact with the server.')
        setCurrent(null)
      }
    }, POLL_MS)
    return () => {
      stopped = true
      window.clearInterval(timer)
    }
  }, [active, jobId, exportId])

  const start = useCallback(
    async (options: RenderOptions) => {
      if (!jobId) return
      setError(null)
      setStarting(true)
      try {
        setCurrent(await api.startExport(jobId, options))
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'The export could not be started.')
      } finally {
        setStarting(false)
      }
    },
    [jobId],
  )

  const cancel = useCallback(async () => {
    const e = currentRef.current
    if (!jobId || !e) return
    try {
      await api.cancelExport(jobId, e.id)
      setCurrent(await api.getExport(jobId, e.id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The export could not be cancelled.')
    }
  }, [jobId])

  const dismiss = useCallback(() => {
    setCurrent(null)
    setError(null)
  }, [])

  return { current, busy: Boolean(active) || starting, error, start, cancel, dismiss }
}
