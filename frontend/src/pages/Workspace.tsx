import { useCallback, useEffect, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { RenderOptions } from '../api/types'
import { ExportBar } from '../components/ExportBar'
import { InsightsView } from '../components/Insights'
import type { Jump } from '../components/PageViewer'
import { PreviewStage } from '../components/PreviewStage'
import { SettingsPanel } from '../components/SettingsPanel'
import { SourcePanel } from '../components/SourcePanel'
import { useExport } from '../hooks/useExport'
import { useInsights } from '../hooks/useInsights'
import { usePreview } from '../hooks/usePreview'
import { usePreviewPdf } from '../hooks/usePreviewPdf'
import type { Session } from '../hooks/useSession'
import { loadView, saveView, type ViewMode } from '../lib/views'
import { reconcileOptions } from '../state/options'

type Tab = 'settings' | 'preview'
type View = 'preview' | 'insights'

interface Props {
  session: Session
  options: RenderOptions
  setOptions: Dispatch<SetStateAction<RenderOptions>>
}

export function Workspace({ session, options, setOptions }: Props) {
  const [volume, setVolume] = useState(1)
  const [page, setPage] = useState(1)
  const [tab, setTab] = useState<Tab>('settings')
  const [view, setView] = useState<View>('preview')
  const [mode, setMode] = useState<ViewMode>(loadView)
  const changeMode = useCallback((m: ViewMode) => {
    setMode(m)
    saveView(m)
  }, [])

  const job = session.phase === 'ready' ? session.job : null

  // When a chat finishes loading (or is merged with another) make sure the choices still refer to real people.
  useEffect(() => {
    if (job) setOptions((o) => reconcileOptions(o, job))
  }, [job, setOptions])

  const jobId = job?.id ?? null
  const preview = usePreview(jobId, options, volume, page)
  const pdf = usePreviewPdf(jobId, options, volume, page, job?.background?.version ?? '')
  const insights = useInsights(jobId, view === 'insights')
  const exporter = useExport(jobId)
  const stats = preview.data?.stats ?? null

  // Keep the chosen volume inside the range after the volume setting changes.
  useEffect(() => {
    if (stats && volume > Math.max(1, stats.volumes.length)) setVolume(1)
  }, [stats, volume])

  const change = useCallback(
    (patch: Partial<RenderOptions>) => {
      setOptions((o) => ({ ...o, ...patch }))
      setPage(1)
    },
    [setOptions],
  )
  const changeBackground = useCallback(
    (patch: Partial<RenderOptions['background']>) => {
      setOptions((o) => ({ ...o, background: { ...o.background, ...patch } }))
    },
    [setOptions],
  )
  // Cover, back page and design edits keep the section being looked at.
  const changeNested = useCallback(
    <K extends 'design' | 'cover_text' | 'back'>(key: K, patch: Partial<RenderOptions[K]>) => {
      setOptions((o) => ({ ...o, [key]: { ...o[key], ...patch } }))
    },
    [setOptions],
  )
  const lastSection = preview.data?.page_count ?? 1
  const [jump, setJump] = useState<Jump | null>(null)
  const showPart = useCallback(
    (part: 'cover' | 'back') => {
      const target = part === 'cover' ? 1 : lastSection
      setPage(target)
      setJump((j) => ({ to: part === 'cover' ? 'first' : 'last', token: (j?.token ?? 0) + 1, immediate: page === target }))
    },
    [lastSection, page],
  )
  const changeAlbum = useCallback(
    (patch: Partial<RenderOptions['album']>) => {
      setOptions((o) => ({ ...o, album: { ...o.album, ...patch } }))
      setPage(1)
    },
    [setOptions],
  )

  const hasChat = Boolean(job)

  return (
    <div className={`workspace${hasChat ? ' has-chat' : ''}`} data-tab={tab}>
      <main className="layout">
        <aside className="side" aria-label="Settings">
          <div className="side-scroll">
            <SourcePanel session={session} />
            {job && (
              <SettingsPanel
                job={job}
                options={options}
                stats={stats}
                onChange={change}
                onAlbum={changeAlbum}
                onBackground={changeBackground}
                onNested={changeNested}
                onShow={showPart}
                onPicture={session.setBackground}
                onRemovePicture={session.removeBackground}
              />
            )}
          </div>
          {job && (
            <div className="side-foot">
              <ExportBar jobId={job.id} options={options} stats={stats} exporter={exporter} disabled={preview.loading && !stats} />
            </div>
          )}
        </aside>

        <section className="paper" aria-label="Preview">
          {job ? (
            <div className="paper-col">
              <div className="viewtabs" role="tablist" aria-label="What to show">
                <button type="button" role="tab" aria-selected={view === 'preview'} className={view === 'preview' ? 'on' : ''} onClick={() => setView('preview')}>
                  Preview
                </button>
                <button type="button" role="tab" aria-selected={view === 'insights'} className={view === 'insights' ? 'on' : ''} onClick={() => setView('insights')}>
                  Insights
                </button>
              </div>
              {view === 'preview' ? (
                <PreviewStage
                  pdf={pdf}
                  stats={stats}
                  sections={preview.data?.page_count ?? 1}
                  sectionInfo={preview.data?.sections ?? []}
                  volume={volume}
                  section={page}
                  mode={mode}
                  onMode={changeMode}
                  onVolume={(v) => {
                    setVolume(v)
                    setPage(1)
                  }}
                  onSection={setPage}
                  jump={jump}
                />
              ) : (
                <div className="stage-scroll">
                  <InsightsView state={insights} />
                </div>
              )}
            </div>
          ) : (
            <div className="welcome">
              <h1>Drop in a chat to begin</h1>
              <p>Export a chat from WhatsApp, Instagram or Facebook with media, then drop the .zip on the left. Your settings are remembered for next time.</p>
              <ul>
                <li>
                  <b>Preview first.</b> The pages update as you change paper, style and filters.
                </li>
                <li>
                  <b>Insights.</b> See who talks most, busiest days and favourite hours.
                </li>
                <li>
                  <b>No chat handy?</b> Use “try a sample chat” on the left.
                </li>
              </ul>
            </div>
          )}
        </section>
      </main>

      {hasChat && (
        <nav className="tabs" aria-label="Switch between settings and preview">
          <button type="button" className={tab === 'settings' ? 'on' : ''} onClick={() => setTab('settings')}>
            Settings
          </button>
          <button type="button" className={tab === 'preview' ? 'on' : ''} onClick={() => setTab('preview')}>
            Preview
          </button>
        </nav>
      )}
    </div>
  )
}