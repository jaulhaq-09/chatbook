import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { DateOrder, Job } from '../api/types'

export type Phase = 'empty' | 'uploading' | 'processing' | 'ready' | 'failed'

export interface Session {
  job: Job | null
  phase: Phase
  /** 0..1 while files are being sent to the server. */
  uploadFraction: number
  error: string | null
  /** True while the page checks whether the chat from the last visit still exists. */
  restoring: boolean
  start: (files: File[]) => Promise<void>
  startSample: () => Promise<void>
  addFiles: (files: File[]) => Promise<void>
  setDateOrder: (order: DateOrder) => Promise<void>
  /** Resolve to an error message, or null when it worked. */
  setBackground: (file: File) => Promise<string | null>
  removeBackground: () => Promise<string | null>
  openJob: (id: string) => Promise<void>
  reset: () => Promise<void>
}

const POLL_MS = 700
const KEY = 'chatbook.job'

function remembered(): string | null {
  try {
    const id = localStorage.getItem(KEY)
    return id && /^[0-9a-f]{32}$/.test(id) ? id : null
  } catch {
    return null
  }
}

function remember(id: string | null): void {
  try {
    if (id) localStorage.setItem(KEY, id)
    else localStorage.removeItem(KEY)
  } catch {
    /* storage can be blocked; the chat just will not be resumed */
  }
}

/** Owns the loaded chat: upload, background processing (polled), merge and removal. */
export function useSession(): Session {
  const [job, setJob] = useState<Job | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadFraction, setUploadFraction] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [restoring, setRestoring] = useState<boolean>(() => remembered() !== null)
  const jobRef = useRef<Job | null>(null)
  jobRef.current = job

  const fail = useCallback((err: unknown) => {
    setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
  }, [])

  const run = useCallback(
    async (task: () => Promise<Job>, keepCurrent: boolean) => {
      setError(null)
      try {
        const next = await task()
        setJob(next)
      } catch (err) {
        if (!keepCurrent) setJob(null)
        fail(err)
      } finally {
        setUploading(false)
      }
    },
    [fail],
  )

  const start = useCallback(
    async (files: File[]) => {
      const old = jobRef.current
      if (old) void api.deleteJob(old.id).catch(() => undefined)
      setJob(null)
      setUploading(true)
      setUploadFraction(0)
      await run(() => api.createJob(files, 'auto', setUploadFraction), false)
    },
    [run],
  )

  const startSample = useCallback(async () => {
    const old = jobRef.current
    if (old) void api.deleteJob(old.id).catch(() => undefined)
    setJob(null)
    setUploading(true)
    setUploadFraction(1)
    await run(() => api.createSample(), false)
  }, [run])

  const addFiles = useCallback(
    async (files: File[]) => {
      const current = jobRef.current
      if (!current) return
      setUploading(true)
      setUploadFraction(0)
      await run(() => api.addFiles(current.id, files, setUploadFraction), true)
    },
    [run],
  )

  const setDateOrder = useCallback(
    async (order: DateOrder) => {
      const current = jobRef.current
      if (!current) return
      await run(() => api.setDateOrder(current.id, order), true)
    },
    [run],
  )

  // The page picture changes the chat in place: it must not bring back the upload screen.
  const changeBackground = useCallback(async (task: (id: string) => Promise<Job>): Promise<string | null> => {
    const current = jobRef.current
    if (!current) return null
    try {
      setJob(await task(current.id))
      return null
    } catch (err) {
      return err instanceof ApiError ? err.message : 'Something went wrong. Try again.'
    }
  }, [])
  const setBackground = useCallback((file: File) => changeBackground((id) => api.setBackground(id, file)), [changeBackground])
  const removeBackground = useCallback(() => changeBackground((id) => api.removeBackground(id)), [changeBackground])

  const openJob = useCallback(
    async (id: string) => {
      setError(null)
      setUploading(false)
      try {
        const next = await api.getJob(id)
        setJob(next)
        remember(next.id)
      } catch (err) {
        fail(err)
      }
    },
    [fail],
  )

  const reset = useCallback(async () => {
    const current = jobRef.current
    setJob(null)
    setError(null)
    if (current) await api.deleteJob(current.id).catch(() => undefined)
  }, [])

  // Pick up where the last visit ended, if that chat has not been deleted yet.
  useEffect(() => {
    const id = remembered()
    if (!id) return
    let cancelled = false
    api
      .getJob(id)
      .then((j) => {
        if (!cancelled && j.status !== 'failed') setJob((cur) => cur ?? j)
      })
      .catch(() => remember(null))
      .finally(() => {
        if (!cancelled) setRestoring(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Remember the current chat for next time.
  useEffect(() => {
    if (job && job.status !== 'failed') remember(job.id)
    else if (!job && !restoring) remember(null)
  }, [job, restoring])

  // Poll while the server is still reading the chat.
  const processing = job?.status === 'processing'
  const jobId = job?.id
  useEffect(() => {
    if (!processing || !jobId) return
    let stopped = false
    const timer = window.setInterval(async () => {
      try {
        const next = await api.getJob(jobId)
        if (!stopped) setJob(next)
      } catch (err) {
        if (stopped) return
        if (err instanceof ApiError && err.status === 404) {
          setJob(null)
          setError('This chat expired and was deleted. Upload it again to continue.')
        }
      }
    }, POLL_MS)
    return () => {
      stopped = true
      window.clearInterval(timer)
    }
  }, [processing, jobId])

  let phase: Phase = 'empty'
  if (uploading) phase = 'uploading'
  else if (job?.status === 'processing') phase = 'processing'
  else if (job?.status === 'ready') phase = 'ready'
  else if (job?.status === 'failed') phase = 'failed'

  return { job, phase, uploadFraction, error, restoring, start, startSample, addFiles, setDateOrder, setBackground, removeBackground, openJob, reset }
}