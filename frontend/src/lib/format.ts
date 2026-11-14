/** Small formatting helpers used across the UI. */

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  return `${value >= 100 ? Math.round(value) : value.toFixed(1)} ${units[i]}`
}

export function plural(n: number, word: string): string {
  return `${n.toLocaleString('en-GB')} ${word}${n === 1 ? '' : 's'}`
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function parts(iso: string): { d: number; m: number; y: number } {
  // Dates are written without a time zone by the server; read the digits, never shift them.
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return { d, m, y }
}

/** "12 Mar – 18 Apr 2026", "12 Mar 2025 – 3 Jan 2026" or "12 Mar 2026". */
export function formatRange(startIso: string, endIso: string): string {
  const a = parts(startIso)
  const b = parts(endIso)
  const left = (withYear: boolean) => `${a.d} ${MONTHS[a.m - 1]}${withYear ? ` ${a.y}` : ''}`
  const right = `${b.d} ${MONTHS[b.m - 1]} ${b.y}`
  if (a.y === b.y && a.m === b.m && a.d === b.d) return right
  return `${left(a.y !== b.y)} – ${right}`
}

/** "Deleted automatically at 10:42 pm" from an ISO timestamp with a time zone. */
export function expiryLabel(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'Deleted automatically after a day'
  const time = date.toLocaleTimeString('en-GB', { hour: 'numeric', minute: '2-digit', hour12: true })
  return `Deleted automatically at ${time.replace(/ /g, ' ').toLowerCase()}`
}

/** Turn a FastAPI error body into one readable sentence. */
export function describeError(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: unknown[]; msg?: string }
    const where = Array.isArray(first.loc) ? first.loc.filter((p) => p !== 'body').join('.') : ''
    return `${where ? where + ': ' : ''}${first.msg ?? 'The request was not valid.'}`
  }
  return 'Something went wrong. Try again.'
}

export function pagesLabel(pages: number): string {
  return `about ${plural(pages, 'page')}`
}

/** "Tue 3 Mar 2026" from a YYYY-MM-DD string, without time zone shifting. */
export function formatDay(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  const dow = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][new Date(Date.UTC(y, m - 1, d)).getUTCDay()]
  return `${dow} ${d} ${MONTHS[m - 1]} ${y}`
}

/** "9 am", "12 pm", "11 pm" for an hour 0 to 23. */
export function hourLabel(h: number): string {
  const suffix = h < 12 ? 'am' : 'pm'
  return `${h % 12 === 0 ? 12 : h % 12} ${suffix}`
}

/** Percentage with no decimals, never NaN. */
export function share(part: number, whole: number): number {
  return whole > 0 ? Math.round((part / whole) * 100) : 0
}