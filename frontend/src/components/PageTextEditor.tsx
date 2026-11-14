import type { BackOptions, CoverText, LeftFooter, RenderOptions, RightFooter } from '../api/types'
import { Field, Section, Switch } from './ui'

type Nested = <K extends 'cover_text' | 'back'>(key: K, patch: Partial<RenderOptions[K]>) => void

interface Props {
  options: RenderOptions
  /** What the automatic text would say, shown as the grey hint in a blank field. */
  auto: { dates: string; people: string; summary: string; title: string }
  onNested: Nested
  onChange: (patch: Partial<RenderOptions>) => void
  /** Called when a field of the cover or back page gets focus, so the preview can show that page. */
  onShow: (part: 'cover' | 'back') => void
}

function Text({
  label,
  value,
  placeholder,
  max,
  lines,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  max: number
  lines?: number
  onChange: (v: string) => void
}) {
  return (
    <Field label={label}>
      {lines ? (
        <textarea rows={lines} value={value} maxLength={max} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input type="text" value={value} maxLength={max} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      )}
    </Field>
  )
}

const LEFT: { value: LeftFooter; label: string }[] = [
  { value: 'people', label: 'The people’s names' },
  { value: 'text', label: 'My own text' },
  { value: 'none', label: 'Nothing' },
]
const RIGHT: { value: RightFooter; label: string }[] = [
  { value: 'counts', label: 'Message, photo and video counts' },
  { value: 'dates', label: 'The dates' },
  { value: 'text', label: 'My own text' },
  { value: 'none', label: 'Nothing' },
]

/** What goes in the bottom-left and bottom-right corners: automatic text, the person's own words, or nothing. */
function Footer({
  value,
  auto,
  onChange,
}: {
  value: Pick<CoverText, 'left_mode' | 'right_mode' | 'footer_left' | 'footer_right'>
  auto: Props['auto']
  onChange: (patch: Partial<Pick<CoverText, 'left_mode' | 'right_mode' | 'footer_left' | 'footer_right'>>) => void
}) {
  return (
    <>
      <Field label="Bottom-left corner">
        <select value={value.left_mode} onChange={(e) => onChange({ left_mode: e.target.value as LeftFooter })}>
          {LEFT.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {value.left_mode === 'text' && (
          <input type="text" className="below" value={value.footer_left} maxLength={120} placeholder={auto.people} onChange={(e) => onChange({ footer_left: e.target.value })} />
        )}
      </Field>
      <Field label="Bottom-right corner">
        <select value={value.right_mode} onChange={(e) => onChange({ right_mode: e.target.value as RightFooter })}>
          {RIGHT.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {value.right_mode === 'text' && (
          <input type="text" className="below" value={value.footer_right} maxLength={120} placeholder="e.g. Made with love" onChange={(e) => onChange({ footer_right: e.target.value })} />
        )}
      </Field>
    </>
  )
}

/** The words on the cover, on the back page and in the running header. */
export function PageTextEditor({ options, auto, onNested, onChange, onShow }: Props) {
  const ct: CoverText = options.cover_text
  const bk: BackOptions = options.back
  const setCover = (patch: Partial<CoverText>) => onNested('cover_text', patch)
  const setBack = (patch: Partial<BackOptions>) => onNested('back', patch)

  return (
    <>
      {options.cover && (
        <Section title="Cover text" fold="closed">
          <div onFocusCapture={() => onShow('cover')}>
            <Text label="Small line above the title" value={ct.kicker} max={80} placeholder="e.g. A story in messages" onChange={(kicker) => setCover({ kicker })} />
            <Text label="Subtitle" value={ct.subtitle} max={120} placeholder={auto.dates} onChange={(subtitle) => setCover({ subtitle })} />
            <Text label="Dedication or tagline" value={ct.tagline} max={200} lines={2} placeholder="e.g. For Mahi, with love" onChange={(tagline) => setCover({ tagline })} />
            <Footer value={ct} auto={auto} onChange={setCover} />
            <p className="note">Leave a field blank to use the automatic text shown in grey.</p>
          </div>
        </Section>
      )}

      <Section title="Back page" fold="closed">
        <div onFocusCapture={() => bk.enabled && onShow('back')}>
          <Switch label="Add a back page" hint="A closing page after the last message" checked={bk.enabled} onChange={(enabled) => setBack({ enabled })} />
          {bk.enabled && (
            <>
              <Text label="Heading" value={bk.heading} max={80} placeholder="The end" onChange={(heading) => setBack({ heading })} />
              <Text label="Message" value={bk.message} max={400} lines={3} placeholder={auto.dates} onChange={(message) => setBack({ message })} />
              <Text label="Signature" value={bk.signature} max={120} placeholder="e.g. Jaul" onChange={(signature) => setBack({ signature })} />
              <Footer value={bk} auto={auto} onChange={setBack} />
            </>
          )}
        </div>
      </Section>

      <Section title="Page header" fold="closed">
        <Text label="Header, left" value={options.header_left} max={120} placeholder={auto.title} onChange={(header_left) => onChange({ header_left })} />
        <Text label="Header, right" value={options.header_right} max={120} placeholder={auto.dates} onChange={(header_right) => onChange({ header_right })} />
        <p className="note">The small line at the top of every page. Leave blank for the automatic text.</p>
      </Section>
    </>
  )
}