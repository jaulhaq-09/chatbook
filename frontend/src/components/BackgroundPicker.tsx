import { useRef, useState, type DragEvent } from 'react'
import { api } from '../api/client'
import type { BackgroundInfo, BackgroundOptions } from '../api/types'
import { Field, Icon, Section, Segmented, Spinner, Switch } from './ui'

const MAX_BYTES = 25 * 1024 * 1024
const ACCEPT = 'image/png,image/jpeg,image/webp'

interface Props {
  jobId: string
  picture: BackgroundInfo | null
  options: BackgroundOptions
  onOptions: (patch: Partial<BackgroundOptions>) => void
  onPicture: (file: File) => Promise<string | null>
  onRemove: () => Promise<string | null>
}

/** Choose a picture to print faintly behind every page, and how it sits there. */
export function BackgroundPicker({ jobId, picture, options, onOptions, onPicture, onRemove }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [over, setOver] = useState(false)

  const choose = async (file: File | undefined) => {
    if (!file) return
    if (!/^image\//.test(file.type) && !/\.(png|jpe?g|webp)$/i.test(file.name)) {
      setError('Choose a JPG, PNG or WebP picture.')
      return
    }
    if (file.size > MAX_BYTES) {
      setError('That picture is larger than 25 MB. Choose a smaller one.')
      return
    }
    setBusy(true)
    setError(null)
    const failed = await onPicture(file)
    setBusy(false)
    if (failed) setError(failed)
    else onOptions({ enabled: true })
  }

  const remove = async () => {
    setBusy(true)
    setError(null)
    const failed = await onRemove()
    setBusy(false)
    if (failed) setError(failed)
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setOver(false)
    void choose(e.dataTransfer.files[0])
  }

  const percent = Math.round(options.opacity * 100)

  return (
    <Section title="Background picture">
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        hidden
        onChange={(e) => {
          void choose(e.target.files?.[0])
          e.target.value = ''
        }}
      />

      {!picture ? (
        <button
          type="button"
          className={`bg-pick${over ? ' over' : ''}`}
          disabled={busy}
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setOver(true)
          }}
          onDragLeave={() => setOver(false)}
          onDrop={onDrop}
        >
          {busy ? <Spinner small /> : <Icon name="upload" />}
          <span>
            <strong>{busy ? 'Adding the picture' : 'Add a picture'}</strong>
            <small>It is printed faintly behind every page. JPG, PNG or WebP.</small>
          </span>
        </button>
      ) : (
        <>
          <div className="bg-card">
            <img src={api.backgroundUrl(jobId, picture.version)} alt="" width={64} height={64} />
            <div className="grow">
              <strong title={picture.name}>{picture.name}</strong>
              <small>
                {picture.width} × {picture.height} px
              </small>
            </div>
            <button type="button" className="link" disabled={busy} onClick={() => input.current?.click()}>
              Replace
            </button>
            <button type="button" className="icon-btn" disabled={busy} onClick={() => void remove()} aria-label="Remove the picture" title="Remove the picture">
              <Icon name="x" />
            </button>
          </div>

          <Switch label="Show it on the pages" checked={options.enabled} onChange={(enabled) => onOptions({ enabled })} />

          {options.enabled && (
            <>
              <Field label="How it fills the page">
                <Segmented
                  label="How the picture fills the page"
                  value={options.fit}
                  onChange={(fit) => onOptions({ fit })}
                  options={[
                    { value: 'cover', label: 'Fill page', hint: 'Covers the whole page. Edges may be cropped.' },
                    { value: 'contain', label: 'Fit inside', hint: 'Shows the whole picture, with plain paper around it.' },
                    { value: 'tile', label: 'Repeat', hint: 'A pattern of small copies' },
                  ]}
                />
              </Field>
              <Field label={`Strength ${percent}%`} note="Lower is fainter and easier to read the chat over.">
                <input
                  type="range"
                  className="range"
                  min={5}
                  max={100}
                  step={5}
                  value={percent}
                  aria-label="Picture strength"
                  onChange={(e) => onOptions({ opacity: Number(e.target.value) / 100 })}
                />
              </Field>
              <Field label="Which pages">
                <Segmented
                  label="Which pages"
                  value={options.scope}
                  onChange={(scope) => onOptions({ scope })}
                  options={[
                    { value: 'all', label: 'All' },
                    { value: 'inside', label: 'Inside only' },
                    { value: 'cover', label: 'Covers only' },
                  ]}
                />
              </Field>
            </>
          )}
        </>
      )}

      {error && (
        <p className="note error" role="alert">
          {error}
        </p>
      )}
    </Section>
  )
}