import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import type { SectionInfo } from '../api/types'
import { sectionForDate, sectionForPage } from '../lib/sections'

interface Props {
  sections: SectionInfo[]
  /** Estimated number of pages in the whole volume. */
  totalPages: number
  onSection: (section: number) => void
}

/** "Go to" box: jump to a page number or a date instead of stepping through dozens of sections. */
export function GoTo({ sections, totalPages, onSection }: Props) {
  const [open, setOpen] = useState(false)
  const [page, setPage] = useState('')
  const root = useRef<HTMLDivElement>(null)
  const panelId = useId()
  const first = sections[0]?.start.slice(0, 10)
  const last = sections[sections.length - 1]?.end.slice(0, 10)

  useEffect(() => {
    if (!open) return
    const outside = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false)
    }
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', outside)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', outside)
      document.removeEventListener('keydown', esc)
    }
  }, [open])

  const jump = (section: number) => {
    onSection(section)
    setOpen(false)
  }

  const submitPage = (e: FormEvent) => {
    e.preventDefault()
    const n = Number(page)
    if (!Number.isFinite(n) || n < 1) return
    jump(sectionForPage(sections, totalPages, n))
    setPage('')
  }

  return (
    <div className="viewmenu" ref={root}>
      <button type="button" className="btn view-btn" aria-haspopup="dialog" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((o) => !o)}>
        <span>Go to</span>
      </button>
      {open && (
        <div className="menu goto" id={panelId} role="dialog" aria-label="Go to">
          <form onSubmit={submitPage}>
            <label htmlFor={`${panelId}-page`}>Page number</label>
            <div className="goto-row">
              <input
                id={`${panelId}-page`}
                type="number"
                inputMode="numeric"
                min={1}
                max={Math.max(1, totalPages)}
                placeholder={`1 to ${totalPages.toLocaleString('en-GB')}`}
                value={page}
                autoFocus
                onChange={(e) => setPage(e.target.value)}
              />
              <button type="submit" className="btn primary" disabled={!page}>
                Go
              </button>
            </div>
            <small>Page numbers are estimates until the pages are made, so the page may be a few off.</small>
          </form>
          <hr />
          <label htmlFor={`${panelId}-date`}>Date</label>
          <input id={`${panelId}-date`} type="date" min={first} max={last} onChange={(e) => e.target.value && jump(sectionForDate(sections, e.target.value))} />
          <small>Opens the part of the chat that covers that day.</small>
        </div>
      )}
    </div>
  )
}