import { describeError } from '../lib/format'
import type { DateOrder, ExportJob, Insights, Job, Preview, RenderOptions } from './types'

const BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function failure(res: Response): Promise<ApiError> {
  let detail: unknown
  try {
    detail = (await res.json()).detail
  } catch {
    detail = undefined
  }
  return new ApiError(res.status, describeError(detail))
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, init)
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'The server cannot be reached. Check that the backend is running.')
  }
  if (!res.ok) throw await failure(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

const json = (body: unknown, method = 'POST'): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

/** Upload with progress. fetch() cannot report upload progress, so this uses XMLHttpRequest. */
function upload(path: string, form: FormData, onProgress?: (fraction: number) => void): Promise<Job> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', BASE + path)
    xhr.responseType = 'json'
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total)
    }
    xhr.onerror = () => reject(new ApiError(0, 'The upload failed. Check that the backend is running.'))
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as Job)
      else reject(new ApiError(xhr.status, describeError(xhr.response?.detail)))
    }
    xhr.send(form)
  })
}

function filesForm(files: File[], extra: Record<string, string> = {}): FormData {
  const form = new FormData()
  files.forEach((f) => form.append('files', f, f.name))
  Object.entries(extra).forEach(([k, v]) => form.append(k, v))
  return form
}

export const api = {
  createJob: (files: File[], dateOrder: DateOrder, onProgress?: (fraction: number) => void) =>
    upload('/jobs', filesForm(files, { date_order: dateOrder }), onProgress),
  createSample: () => request<Job>('/jobs/sample', { method: 'POST' }),
  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  addFiles: (id: string, files: File[], onProgress?: (fraction: number) => void) =>
    upload(`/jobs/${id}/files`, filesForm(files), onProgress),
  setDateOrder: (id: string, dateOrder: DateOrder) => request<Job>(`/jobs/${id}`, json({ date_order: dateOrder }, 'PATCH')),
  /** Keep a picture to print behind the pages. */
  setBackground: (id: string, file: File, onProgress?: (fraction: number) => void) => {
    const form = new FormData()
    form.append('file', file, file.name)
    return upload(`/jobs/${id}/background`, form, onProgress)
  },
  removeBackground: (id: string) => request<Job>(`/jobs/${id}/background`, { method: 'DELETE' }),
  backgroundUrl: (id: string, version: string) => `${BASE}/jobs/${id}/background?v=${encodeURIComponent(version)}`,
  deleteJob: (id: string) => request<void>(`/jobs/${id}`, { method: 'DELETE' }),

  insights: (id: string, signal?: AbortSignal) => request<Insights>(`/jobs/${id}/insights`, { signal }),

  preview: (id: string, options: RenderOptions, volume: number, page: number, signal?: AbortSignal) =>
    request<Preview>(`/jobs/${id}/preview`, { ...json({ options, volume, page }), signal }),

  /** The pages of one section as PDF bytes, for the page viewer. */
  previewPdf: async (id: string, options: RenderOptions, volume: number, page: number, signal?: AbortSignal) => {
    let res: Response
    try {
      res = await fetch(`${BASE}/jobs/${id}/preview-pdf`, { ...json({ options, volume, page }), signal })
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') throw err
      throw new ApiError(0, 'The server cannot be reached. Check that the backend is running.')
    }
    if (!res.ok) throw await failure(res)
    return res.arrayBuffer()
  },

  startExport: (id: string, options: RenderOptions) => request<ExportJob>(`/jobs/${id}/exports`, json(options)),
  getExport: (id: string, exportId: string) => request<ExportJob>(`/jobs/${id}/exports/${exportId}`),
  cancelExport: (id: string, exportId: string) => request<void>(`/jobs/${id}/exports/${exportId}`, { method: 'DELETE' }),
  fileUrl: (id: string, exportId: string, name: string, inline = false) =>
    `${BASE}/jobs/${id}/exports/${exportId}/files/${encodeURIComponent(name)}${inline ? '?inline=true' : ''}`,
}