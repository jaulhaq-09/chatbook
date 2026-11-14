import type { Job, RenderOptions, Stats } from '../api/types'
import { formatRange, plural } from '../lib/format'
import { volumeUnit } from '../state/options'
import { BackgroundPicker } from './BackgroundPicker'
import { ChatFontField, DesignPicker } from './DesignPicker'
import { PageTextEditor } from './PageTextEditor'
import { Field, Section, Segmented, Switch } from './ui'

interface Props {
  job: Job
  options: RenderOptions
  stats: Stats | null
  onChange: (patch: Partial<RenderOptions>) => void
  onAlbum: (patch: Partial<RenderOptions['album']>) => void
  onBackground: (patch: Partial<RenderOptions['background']>) => void
  onNested: <K extends 'design' | 'cover_text' | 'back'>(key: K, patch: Partial<RenderOptions[K]>) => void
  onShow: (part: 'cover' | 'back') => void
  onPicture: (file: File) => Promise<string | null>
  onRemovePicture: () => Promise<string | null>
}

const toDate = (v: string) => (v ? v : null)

export function SettingsPanel({ job, options, stats, onChange, onAlbum, onBackground, onNested, onShow, onPicture, onRemovePicture }: Props) {
  const album = options.mode === 'album'
  const auto = {
    dates: job.date_range ? formatRange(job.date_range.start, job.date_range.end) : '',
    people: job.senders.slice(0, 6).map((s) => s.name).join(', '),
    summary: stats ? [plural(stats.messages, 'message'), stats.photos > 0 && plural(stats.photos, 'photo'), stats.videos > 0 && plural(stats.videos, 'video')].filter(Boolean).join(', ') : '',
    title: job.suggested_title || 'Chat',
  }
  const first = job.date_range?.start.slice(0, 10)
  const last = job.date_range?.end.slice(0, 10)
  const toggleExcluded = (name: string, excluded: boolean) =>
    onChange({
      exclude_people: excluded ? [...options.exclude_people, name] : options.exclude_people.filter((n) => n !== name),
    })

  return (
    <div className="settings">
      <Section title="Output">
        <Segmented
          label="What to make"
          value={options.mode}
          onChange={(mode) => onChange({ mode })}
          options={[
            { value: 'book', label: 'Chat book', hint: 'The conversation as it looks in WhatsApp' },
            { value: 'album', label: 'Photo album', hint: 'Only the photos and videos, as a grid' },
          ]}
        />
        <Field label="Title">
          <input
            type="text"
            value={options.title}
            maxLength={120}
            placeholder={job.suggested_title || 'Title on the cover'}
            onChange={(e) => onChange({ title: e.target.value })}
          />
        </Field>
      </Section>

      <Section title="Layout">
        <Field label="Paper">
          <Segmented
            label="Paper size"
            value={options.page_size}
            onChange={(page_size) => onChange({ page_size })}
            options={[
              { value: 'A4', label: 'A4' },
              { value: 'Letter', label: 'Letter' },
              { value: 'A5', label: 'A5' },
              { value: 'Square', label: 'Square' },
            ]}
          />
        </Field>

        <ChatFontField value={options.chat_font} onChange={(chat_font) => onChange({ chat_font })} />

        {!album && (
          <>
            <Field label="Style">
              <Segmented
                label="Style"
                value={options.theme}
                onChange={(theme) => onChange({ theme })}
                options={[
                  { value: 'classic', label: 'Classic', hint: 'Warm paper and green bubbles, like the app' },
                  { value: 'clean', label: 'Clean', hint: 'White paper, light grey bubbles' },
                  { value: 'ink', label: 'Ink saver', hint: 'Almost no colour, cheap to print' },
                ]}
              />
            </Field>
            <Field label="Text size">
              <Segmented
                label="Text size"
                value={options.text_size}
                onChange={(text_size) => onChange({ text_size })}
                options={[
                  { value: 's', label: 'Small' },
                  { value: 'm', label: 'Medium' },
                  { value: 'l', label: 'Large' },
                ]}
              />
            </Field>
            <Field label="Right-hand side is" note="WhatsApp does not record who exported the chat. Pick yourself.">
              <select value={options.me ?? ''} onChange={(e) => onChange({ me: e.target.value || null })}>
                {job.senders.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Clock">
              <Segmented
                label="Clock"
                value={options.clock}
                onChange={(clock) => onChange({ clock })}
                options={[
                  { value: 'h12', label: '9:41 pm' },
                  { value: 'h24', label: '21:41' },
                ]}
              />
            </Field>
            <Switch label="Show photos and videos" checked={options.show_media} onChange={(show_media) => onChange({ show_media })} />
          </>
        )}

        {album && (
          <>
            <Field label="Group by">
              <Segmented
                label="Group by"
                value={options.album.group}
                onChange={(group) => onAlbum({ group })}
                options={[
                  { value: 'month', label: 'Month' },
                  { value: 'day', label: 'Day' },
                  { value: 'sender', label: 'Person' },
                  { value: 'none', label: 'None' },
                ]}
              />
            </Field>
            <Field label="Photos per row">
              <Segmented
                label="Photos per row"
                value={options.album.columns}
                onChange={(columns) => onAlbum({ columns })}
                options={[
                  { value: 1, label: '1' },
                  { value: 2, label: '2' },
                  { value: 3, label: '3' },
                  { value: 4, label: '4' },
                ]}
              />
            </Field>
            <Field label="Photo shape">
              <Segmented
                label="Photo shape"
                value={options.album.fit}
                onChange={(fit) => onAlbum({ fit })}
                options={[
                  { value: 'fill', label: 'Square crop' },
                  { value: 'fit', label: 'Whole photo' },
                ]}
              />
            </Field>
            <Field label="Paper colour">
              <Segmented
                label="Paper colour"
                value={options.album.paper}
                onChange={(paper) => onAlbum({ paper })}
                options={[
                  { value: 'white', label: 'White' },
                  { value: 'warm', label: 'Warm' },
                  { value: 'black', label: 'Black' },
                ]}
              />
            </Field>
            <Switch label="Captions" hint="Sender and date under each photo" checked={options.album.captions} onChange={(captions) => onAlbum({ captions })} />
            <Switch
              label="Include videos"
              hint={job.video_posters ? 'Shown as a still frame with a play mark' : 'Shown as a plain tile. Install ffmpeg for still frames.'}
              checked={options.album.include_videos}
              onChange={(include_videos) => onAlbum({ include_videos })}
            />
          </>
        )}

        <Switch label="Cover page" checked={options.cover} onChange={(cover) => onChange({ cover })} />
        <Switch
          label="Contents page"
          hint={stats && !stats.toc_available && options.toc ? 'Needs a longer chat to appear' : 'Month and page number'}
          checked={options.toc}
          onChange={(toc) => onChange({ toc })}
        />
        <Switch label="Page numbers" checked={options.page_numbers} onChange={(page_numbers) => onChange({ page_numbers })} />
      </Section>

      <DesignPicker design={options.design} onChange={(patch) => onNested('design', patch)} />
      <PageTextEditor options={options} auto={auto} onNested={onNested} onChange={onChange} onShow={onShow} />

      <BackgroundPicker
        jobId={job.id}
        picture={job.background}
        options={options.background}
        onOptions={onBackground}
        onPicture={onPicture}
        onRemove={onRemovePicture}
      />

      <Section title="Filter">
        <div className="two">
          <Field label="From">
            <input type="date" value={options.date_from ?? ''} min={first} max={options.date_to ?? last} onChange={(e) => onChange({ date_from: toDate(e.target.value) })} />
          </Field>
          <Field label="To">
            <input type="date" value={options.date_to ?? ''} min={options.date_from ?? first} max={last} onChange={(e) => onChange({ date_to: toDate(e.target.value) })} />
          </Field>
        </div>
        {!album && (
          <Field label="Contains the words">
            <input type="search" value={options.query} maxLength={200} placeholder="e.g. birthday" onChange={(e) => onChange({ query: e.target.value })} />
          </Field>
        )}
        {job.senders.length > 1 && (
          <Field label="People" note="Untick someone to leave their messages out.">
            <ul className="people">
              {job.senders.map((s) => {
                const excluded = options.exclude_people.includes(s.name)
                return (
                  <li key={s.name}>
                    <label>
                      <input type="checkbox" checked={!excluded} onChange={(e) => toggleExcluded(s.name, !e.target.checked)} />
                      <span className="grow">{s.name}</span>
                      <small>{s.count.toLocaleString('en-GB')}</small>
                    </label>
                  </li>
                )
              })}
            </ul>
          </Field>
        )}
      </Section>

      <Section title="Print quality and size">
        <Field label="Photo quality" note={options.quality === 'print' ? 'Sharper photos for printing. The file is larger.' : 'Good for reading on screen and everyday printing.'}>
          <Segmented
            label="Photo quality"
            value={options.quality}
            onChange={(quality) => onChange({ quality })}
            options={[
              { value: 'standard', label: 'Standard' },
              { value: 'print', label: 'High (print)' },
            ]}
          />
        </Field>
        <Field
          label="Split into volumes"
          note={
            stats && stats.volumes.length > 1
              ? `${plural(stats.volumes.length, 'volume')}, downloaded together as one .zip.`
              : 'Recommended for chats over a few thousand messages.'
          }
        >
          <select value={options.volume_mode} onChange={(e) => onChange({ volume_mode: e.target.value as RenderOptions['volume_mode'] })}>
            <option value="none">One file</option>
            <option value="month">One per month</option>
            <option value="year">One per year</option>
            <option value="size">By size</option>
          </select>
        </Field>
        {options.volume_mode === 'size' && (
          <Field label={`${album ? 'Photos' : 'Messages'} per volume`}>
            <input
              type="number"
              min={20}
              max={20000}
              step={100}
              value={options.volume_size}
              onChange={(e) => onChange({ volume_size: Math.min(20000, Math.max(20, Number(e.target.value) || 1000)) })}
            />
            <p className="note">Each volume holds about this many {volumeUnit(options.mode)}, split on a day boundary.</p>
          </Field>
        )}
      </Section>
    </div>
  )
}