import type { Job, RenderOptions } from '../api/types'

export const DEFAULT_OPTIONS: RenderOptions = {
  mode: 'book',
  title: '',
  me: null,
  page_size: 'A4',
  theme: 'classic',
  text_size: 'm',
  clock: 'h12',
  show_media: true,
  cover: true,
  toc: true,
  page_numbers: true,
  date_from: null,
  date_to: null,
  exclude_people: [],
  query: '',
  album: { group: 'month', columns: 3, fit: 'fill', paper: 'white', captions: true, include_videos: true },
  background: { enabled: true, fit: 'cover', opacity: 0.3, scope: 'all' },
  chat_font: 'sans',
  design: { cover_style: 'classic', color1: '#0a7556', color2: '#d9a441', heading_font: 'serif', motif: 'bubbles' },
  cover_text: { kicker: '', subtitle: '', tagline: '', left_mode: 'people', right_mode: 'counts', footer_left: '', footer_right: '' },
  back: { enabled: true, heading: 'The end', message: '', signature: '', left_mode: 'people', right_mode: 'dates', footer_left: '', footer_right: '' },
  header_left: '',
  header_right: '',
  quality: 'standard',
  volume_mode: 'none',
  volume_size: 1000,
}

/** WhatsApp does not say who "you" are. The second most active person is the usual guess. */
export function defaultMe(job: Job): string | null {
  return job.senders[1]?.name ?? job.senders[0]?.name ?? null
}

/** Keep the user's choices, but drop anything that no longer exists in the loaded chat. */
export function reconcileOptions(options: RenderOptions, job: Job): RenderOptions {
  const names = new Set(job.senders.map((s) => s.name))
  const me = options.me && names.has(options.me) ? options.me : defaultMe(job)
  const exclude = options.exclude_people.filter((n) => names.has(n))
  if (me === options.me && exclude.length === options.exclude_people.length) return options
  return { ...options, me, exclude_people: exclude }
}

/** What one volume holds, for labels: messages in a book, photos in an album. */
export function volumeUnit(mode: RenderOptions['mode']): string {
  return mode === 'album' ? 'photos' : 'messages'
}

export const PAPER_MM: Record<RenderOptions['page_size'], number> = {
  A4: 210,
  Letter: 215.9,
  A5: 148,
  Square: 200,
}

export const PX_PER_MM = 96 / 25.4

const SAVED_KEY = 'chatbook.options'

/** Only the choices that make sense for any chat. Names, dates and search words belong to one chat. */
const REMEMBERED = [
  'mode', 'page_size', 'theme', 'text_size', 'clock', 'show_media', 'cover', 'toc', 'page_numbers',
  'quality', 'volume_mode', 'volume_size', 'album', 'background', 'chat_font', 'design',
] as const

export function pickRemembered(o: RenderOptions): Partial<RenderOptions> {
  const out: Record<string, unknown> = {}
  for (const k of REMEMBERED) out[k] = o[k]
  return out as Partial<RenderOptions>
}

/** Defaults overlaid with whatever the last visit saved. Anything malformed is ignored. */
export function loadOptions(raw: string | null = readSaved()): RenderOptions {
  if (!raw) return DEFAULT_OPTIONS
  try {
    const saved = JSON.parse(raw) as Record<string, unknown>
    const merged: Record<string, unknown> = { ...DEFAULT_OPTIONS }
    for (const k of REMEMBERED) {
      const v = saved[k]
      const d = (DEFAULT_OPTIONS as unknown as Record<string, unknown>)[k]
      if (v === undefined || typeof v !== typeof d) continue
      merged[k] = k === 'album' || k === 'background' || k === 'design' ? { ...(d as object), ...(v as object) } : v
    }
    return merged as unknown as RenderOptions
  } catch {
    return DEFAULT_OPTIONS
  }
}

function readSaved(): string | null {
  try {
    return localStorage.getItem(SAVED_KEY)
  } catch {
    return null
  }
}

export function saveOptions(o: RenderOptions): void {
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify(pickRemembered(o)))
  } catch {
    /* ignore */
  }
}