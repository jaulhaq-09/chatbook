import type { SectionInfo } from '../api/types'

/**
 * Sections are about 250 messages each, so a long chat has dozens. These helpers turn "page 60" or
 * "15 June" into the section to open. Page numbers are estimates (the real count is only known once
 * Chromium has laid the pages out), so each section's page count is scaled to the estimated total.
 */

/** First and last estimated page of every section, scaled so the last one ends on `total`. */
export function pageRanges(sections: SectionInfo[], total: number): { from: number; to: number }[] {
  const sum = sections.reduce((n, s) => n + Math.max(1, s.pages), 0)
  if (sum === 0) return []
  const scale = total > 0 ? total / sum : 1
  let acc = 0
  return sections.map((s) => {
    const from = Math.round(acc * scale) + 1
    acc += Math.max(1, s.pages)
    const to = Math.max(from, Math.round(acc * scale))
    return { from, to }
  })
}

/** 1-based section that holds this page, or the nearest one when it is out of range. */
export function sectionForPage(sections: SectionInfo[], total: number, page: number): number {
  const ranges = pageRanges(sections, total)
  if (ranges.length === 0) return 1
  const p = Math.max(1, Math.min(Math.round(page), ranges[ranges.length - 1].to))
  const i = ranges.findIndex((r) => p >= r.from && p <= r.to)
  return (i === -1 ? ranges.length - 1 : i) + 1
}

/** 1-based section that holds this day (YYYY-MM-DD). A day in a gap goes to the next section. */
export function sectionForDate(sections: SectionInfo[], iso: string): number {
  if (sections.length === 0) return 1
  const i = sections.findIndex((s) => iso <= s.end.slice(0, 10))
  return (i === -1 ? sections.length - 1 : i) + 1
}