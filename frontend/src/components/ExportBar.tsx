import { api } from '../api/client'
import type { RenderOptions, Stats } from '../api/types'
import type { ExportController } from '../hooks/useExport'
import { formatBytes, pagesLabel, plural } from '../lib/format'
import { Icon, Spinner } from './ui'

interface Props {
  jobId: string
  options: RenderOptions
  stats: Stats | null
  exporter: ExportController
  disabled: boolean
}

export function ExportBar({ jobId, options, stats, exporter, disabled }: Props) {
  const { current, busy, error } = exporter
  const done = current?.status === 'done' ? current : null
  const label = options.mode === 'album' ? 'Make photo album PDF' : 'Make PDF'

  if (busy && current) {
    const p = current.progress
    const pct = p.total > 0 ? Math.round((p.done / p.total) * 100) : 0
    return (
      <div className="export busy" aria-live="polite">
        <div className="export-row">
          <Spinner small />
          <div className="grow">
            <strong>{current.status === 'queued' ? 'Waiting for its turn' : p.stage || 'Making your PDF'}</strong>
            <div className="bar" aria-hidden="true">
              <i style={{ width: `${Math.max(4, pct)}%` }} />
            </div>
          </div>
          <button type="button" className="btn ghost" onClick={() => void exporter.cancel()}>
            Cancel
          </button>
        </div>
      </div>
    )
  }

  if (done) {
    const archive = done.archive
    const single = done.files.length === 1 ? done.files[0] : null
    return (
      <div className="export done">
        <div className="export-row">
          <span className="ok">
            <Icon name="check" />
          </span>
          <div className="grow">
            <strong>Your PDF is ready</strong>
            <small>
              {single
                ? `${plural(single.pages, 'page')}, ${formatBytes(single.size)}`
                : `${plural(done.files.length, 'volume')}, ${plural(done.files.reduce((n, f) => n + f.pages, 0), 'page')} in total`}
            </small>
          </div>
          <button type="button" className="icon-btn" onClick={exporter.dismiss} aria-label="Close">
            <Icon name="x" />
          </button>
        </div>
        {single && (
          <div className="export-actions">
            <a className="btn primary" href={api.fileUrl(jobId, done.id, single.name)} download>
              <Icon name="download" /> Download
            </a>
            <a className="btn" href={api.fileUrl(jobId, done.id, single.name, true)} target="_blank" rel="noreferrer">
              <Icon name="open" /> Open
            </a>
          </div>
        )}
        {!single && (
          <>
            {archive && (
              <div className="export-actions">
                <a className="btn primary" href={api.fileUrl(jobId, done.id, archive)} download>
                  <Icon name="download" /> Download all (.zip)
                </a>
              </div>
            )}
            <ul className="files">
              {done.files.map((f) => (
                <li key={f.name}>
                  <span className="grow">
                    {f.label}
                    <small>
                      {plural(f.pages, 'page')}, {formatBytes(f.size)}
                    </small>
                  </span>
                  <a className="icon-btn" href={api.fileUrl(jobId, done.id, f.name, true)} target="_blank" rel="noreferrer" aria-label={`Open ${f.label}`} title="Open">
                    <Icon name="open" />
                  </a>
                  <a className="icon-btn" href={api.fileUrl(jobId, done.id, f.name)} download aria-label={`Download ${f.label}`} title="Download">
                    <Icon name="download" />
                  </a>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    )
  }

  const message =
    error ??
    (current?.status === 'failed' ? current.error || 'The PDF could not be made.' : current?.status === 'cancelled' ? 'The export was cancelled.' : null)

  return (
    <div className="export">
      {message && (
        <p className={`note ${current?.status === 'cancelled' ? '' : 'error'}`} role="alert">
          {message}
        </p>
      )}
      <button type="button" className="btn primary wide" disabled={disabled || !stats || stats.messages === 0} onClick={() => void exporter.start(options)}>
        {label}
      </button>
      {stats && stats.messages > 0 && (
        <small className="export-hint">
          {pagesLabel(stats.estimated_pages)}
          {stats.volumes.length > 1 ? ` in ${plural(stats.volumes.length, 'volume')}` : ''}
          {stats.estimated_pages > 600 && stats.volumes.length <= 1 ? '. Splitting by month makes this faster and easier to print.' : ''}
        </small>
      )}
    </div>
  )
}
