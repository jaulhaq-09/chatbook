import { lazy, Suspense, useState } from 'react'
import type { SectionInfo, Stats } from '../api/types'
import type { PdfState } from '../hooks/usePreviewPdf'
import { formatRange, pagesLabel, plural } from '../lib/format'
import type { ViewMode } from '../lib/views'
import { pageRanges } from '../lib/sections'
import { GoTo } from './GoTo'
import type { Jump } from './PageViewer'
import { Icon, Spinner } from './ui'
import { ViewMenu } from './ViewMenu'

interface Props {
  pdf: PdfState
  stats: Stats | null
  /** Number of preview sections in this volume (a section is about 250 messages). */
  sections: number
  /** Dates and media counts of every section, for the section picker. */
  sectionInfo: SectionInfo[]
  volume: number
  section: number
  mode: ViewMode
  onMode: (mode: ViewMode) => void
  onVolume: (v: number) => void
  onSection: (p: number) => void
  /** Show the cover or the back page, once the section's pages are on screen. */
  jump?: Jump | null
}

// pdf.js is large, so the viewer is fetched only when a chat is open. The home page never pays for it.
const PageViewer = lazy(() => import('./PageViewer').then((m) => ({ default: m.PageViewer })))

function sectionLabel(n: number, info: SectionInfo | undefined): string {
  if (!info) return `Section ${n}`
  const media = [info.photos > 0 && plural(info.photos, 'photo'), info.videos > 0 && plural(info.videos, 'video')].filter(Boolean).join(', ')
  return `${n}. ${formatRange(info.start, info.end)} · ${media || 'text only'}`
}

/** The printed pages on screen, with the View menu, volume picker and section pager above them. */
export function PreviewStage({ pdf, stats, sections, sectionInfo, volume, section, mode, onMode, onVolume, onSection, jump }: Props) {
  const [shown, setShown] = useState(0)
  const volumes = stats?.volumes ?? []
  const range = pageRanges(sectionInfo, stats?.volumes[volume - 1]?.estimated_pages ?? 0)[section - 1]
  const nothing = pdf.error !== null && pdf.data === null

  return (
    <div className="stage">
      <div className="stage-bar">
        <div className="stage-info">
          {stats ? (
            <>
              <strong>{pagesLabel(stats.estimated_pages)}</strong>
              <span>
                {plural(stats.messages, 'message')}
                {stats.photos > 0 && `, ${plural(stats.photos, 'photo')}`}
                {stats.videos > 0 && `, ${plural(stats.videos, 'video')}`}
                {shown > 0 && sections > 1 && ` · this section: ${plural(shown, 'page')}${range ? `, about pages ${range.from}–${range.to}` : ''}`}
              </span>
            </>
          ) : (
            <span>Preparing preview</span>
          )}
        </div>

        <div className="stage-nav">
          {volumes.length > 1 && (
            <select aria-label="Volume to preview" value={volume} onChange={(e) => onVolume(Number(e.target.value))}>
              {volumes.map((v) => (
                <option key={v.index} value={v.index}>
                  {v.label}
                </option>
              ))}
            </select>
          )}
          {sections > 1 && (
            <div className="pager">
              <button type="button" className="icon-btn" disabled={section <= 1} onClick={() => onSection(section - 1)} aria-label="Previous section">
                <Icon name="chev-l" />
              </button>
              <select aria-label="Section to preview" className="section-select" value={section} onChange={(e) => onSection(Number(e.target.value))}>
                {Array.from({ length: sections }, (_, i) => (
                  <option key={i} value={i + 1}>
                    {sectionLabel(i + 1, sectionInfo[i])}
                  </option>
                ))}
              </select>
              <button type="button" className="icon-btn" disabled={section >= sections} onClick={() => onSection(section + 1)} aria-label="Next section">
                <Icon name="chev-r" />
              </button>
            </div>
          )}
          {sections > 1 && <GoTo sections={sectionInfo} totalPages={stats?.volumes[volume - 1]?.estimated_pages ?? 0} onSection={onSection} />}
          {pdf.loading && <Spinner small />}
          <ViewMenu mode={mode} onChange={onMode} />
        </div>
      </div>

      {pdf.error && !nothing && (
        <p className="note error stage-note" role="alert">
          {pdf.error}
        </p>
      )}

      {nothing ? (
        <div className="stage-empty">
          <strong>{pdf.error?.startsWith('Nothing matches') ? 'Nothing matches these filters' : 'No pages to show'}</strong>
          <span>{pdf.error?.startsWith('Nothing matches') ? 'Widen the dates, tick more people or clear the search words.' : pdf.error}</span>
        </div>
      ) : (
        <div className={`viewer-wrap${pdf.loading ? ' is-loading' : ''}`}>
          <Suspense
            fallback={
              <div className="stage-empty">
                <Spinner />
              </div>
            }
          >
            <PageViewer data={pdf.data} mode={mode} onMode={onMode} onPages={setShown} jump={jump} />
          </Suspense>
        </div>
      )}
    </div>
  )
}