import { useRef, useState, type DragEvent } from 'react'
import type { Session } from '../hooks/useSession'
import { expiryLabel, formatRange, plural } from '../lib/format'
import { Icon, Spinner } from './ui'

const ACCEPT = '.zip,.txt,.json'

function pick(list: FileList | null): File[] {
  return list ? Array.from(list).filter((f) => /\.(zip|txt|json)$/i.test(f.name)) : []
}

/** First thing the person sees: where to drop an export, and later a summary of what was loaded. */
export function SourcePanel({ session }: { session: Session }) {
  const { job, phase, uploadFraction, error } = session
  const input = useRef<HTMLInputElement>(null)
  const addInput = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setOver(false)
    const files = pick(e.dataTransfer.files)
    if (files.length) void (job ? session.addFiles(files) : session.start(files))
  }

  if (phase === 'uploading' || phase === 'processing') {
    const uploading = phase === 'uploading'
    const p = job?.progress
    const fraction = uploading ? uploadFraction : p && p.total > 0 ? p.done / p.total : 0
    return (
      <div className="source busy" aria-live="polite">
        <Spinner />
        <div className="grow">
          <strong>{uploading ? 'Uploading your export' : p?.stage || 'Reading your chat'}</strong>
          <div className="bar" aria-hidden="true">
            <i style={{ width: `${Math.max(3, Math.round(fraction * 100))}%` }} />
          </div>
          <small>
            {uploading
              ? `${Math.round(uploadFraction * 100)}% sent`
              : p && p.total > 0
                ? `${p.done.toLocaleString('en-GB')} of ${p.total.toLocaleString('en-GB')}`
                : 'This can take a minute for very large chats'}
          </small>
        </div>
      </div>
    )
  }

  if (job && phase === 'ready') {
    const counts = job.counts
    return (
      <div className="source loaded">
        <div className="source-head">
          <Icon name="file" />
          <div className="grow">
            <strong title={job.suggested_title}>{job.is_sample ? 'Sample chat' : job.suggested_title || 'Your chat'}</strong>
            <small>{job.date_range ? formatRange(job.date_range.start, job.date_range.end) : 'No dates found'}</small>
          </div>
          <button type="button" className="icon-btn" onClick={() => void session.reset()} aria-label="Remove this chat" title="Remove this chat">
            <Icon name="x" />
          </button>
        </div>
        <dl className="facts">
          <div>
            <dt>Messages</dt>
            <dd>{counts.messages.toLocaleString('en-GB')}</dd>
          </div>
          <div>
            <dt>Photos</dt>
            <dd>{counts.photos.toLocaleString('en-GB')}</dd>
          </div>
          <div>
            <dt>Videos</dt>
            <dd>{counts.videos.toLocaleString('en-GB')}</dd>
          </div>
        </dl>

        {job.sources.length > 1 && <p className="note">{plural(job.sources.length, 'export')} merged. Overlapping messages were removed.</p>}
        {counts.missing_media > 0 && (
          <p className="note warn">{plural(counts.missing_media, 'attachment')} named in the chat {counts.missing_media === 1 ? 'was' : 'were'} not in the export and will show as a placeholder.</p>
        )}
        {counts.omitted_media > 0 && (
          <p className="note">{plural(counts.omitted_media, 'item')} {counts.omitted_media === 1 ? 'was' : 'were'} exported without media, so there is nothing to show.</p>
        )}
        {job.warnings.map((w) => (
          <p className="note warn" key={w}>
            {w}
          </p>
        ))}

        {job.order_ambiguous && (
          <div className="callout">
            <p>
              Dates like <b>03/04/2026</b> can be read two ways. They were read as{' '}
              <b>{job.date_order === 'mdy' ? 'month first' : 'day first'}</b>.
            </p>
            <button type="button" className="link" onClick={() => void session.setDateOrder(job.date_order === 'mdy' ? 'dmy' : 'mdy')}>
              Switch to {job.date_order === 'mdy' ? 'day first' : 'month first'}
            </button>
          </div>
        )}

        <div className="source-foot">
          <button type="button" className="link" onClick={() => addInput.current?.click()}>
            <Icon name="plus" /> Add another export
          </button>
          <small>{expiryLabel(job.expires_at)}</small>
        </div>
        <input
          ref={addInput}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => {
            const files = pick(e.target.files)
            e.target.value = ''
            if (files.length) void session.addFiles(files)
          }}
        />
      </div>
    )
  }

  const failed = phase === 'failed' && job
  return (
    <div className="source empty">
      <div
        className={`drop${over ? ' over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
      >
        <Icon name="upload" />
        <strong>Drop your chat export here</strong>
        <small>WhatsApp, Instagram or Facebook: a .zip with media, or just the chat file (.txt or message_1.json). You can pick several to merge them.</small>
        <button type="button" className="btn primary" onClick={() => input.current?.click()}>
          Choose files
        </button>
        <button type="button" className="link" onClick={() => void session.startSample()}>
          or try a sample chat
        </button>
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => {
            const files = pick(e.target.files)
            e.target.value = ''
            if (files.length) void session.start(files)
          }}
        />
      </div>
      {(error || failed) && (
        <p className="note error" role="alert">
          {error ?? job?.error ?? 'The chat could not be read.'}
        </p>
      )}
      <details className="howto">
        <summary>How do I export a chat from WhatsApp?</summary>
        <p>
          Open the chat, tap the name at the top, then <b>Export chat</b> and choose <b>Include media</b>. Very large chats may be limited by WhatsApp, in which case export in parts and add them together here.
        </p>
      </details>
      <details className="howto">
        <summary>How do I get my Instagram or Facebook chats?</summary>
        <p>
          Open <b>Accounts Centre → Your information and permissions → Download your information</b> (Facebook: <b>Settings → Your Facebook information</b>). Choose <b>Messages</b>, set the format to <b>JSON</b>, the media quality to <b>High</b>, and the date range you want. When Meta emails you the download, upload the .zip here.
        </p>
        <p>
          A download holds all your chats. Chatbook uses the biggest one. To use another, zip just that chat's folder (inside <b>messages → inbox</b>) and upload it.
        </p>
      </details>
    </div>
  )
}