import type { CoverStyle, DesignOptions, Motif } from '../api/types'
import { FONT_CHOICES, SAMPLE_TEXT, fontStack } from '../lib/fonts'
import { PALETTES, isHex, paletteIndex } from '../lib/palettes'
import { Field, Section } from './ui'

interface Props {
  design: DesignOptions
  onChange: (patch: Partial<DesignOptions>) => void
}

const STYLES: { value: CoverStyle; label: string; hint: string }[] = [
  { value: 'classic', label: 'Classic', hint: 'A colour band down the side' },
  { value: 'centered', label: 'Elegant', hint: 'Centred, with a fine double frame' },
  { value: 'bold', label: 'Bold', hint: 'A big two-colour block with the title on it' },
  { value: 'minimal', label: 'Minimal', hint: 'Quiet and modern' },
  { value: 'frame', label: 'Framed', hint: 'A thick border with a soft colour wash' },
]

const MOTIFS: { value: Motif; label: string }[] = [
  { value: 'bubbles', label: 'Chat bubbles' },
  { value: 'hearts', label: 'Hearts' },
  { value: 'sparkles', label: 'Sparkles' },
  { value: 'waves', label: 'Waves' },
  { value: 'rings', label: 'Rings' },
  { value: 'dots', label: 'Dots' },
  { value: 'none', label: 'None' },
]

/** A tiny drawing of each cover, in the chosen colours. */
function Thumb({ style, c1, c2 }: { style: CoverStyle; c1: string; c2: string }) {
  const paper = '#efeae2'
  const ink = '#1c2a33'
  const lines = (x: number, y: number, w: number, anchor: 'start' | 'middle' = 'start') => {
    const left = anchor === 'middle' ? x - w / 2 : x
    return (
      <>
        <rect x={left} y={y} width={w} height="3" rx="1.5" fill={ink} />
        <rect x={anchor === 'middle' ? x - w / 4 : x} y={y + 6} width={w / 2} height="1.6" rx=".8" fill={ink} opacity=".35" />
      </>
    )
  }
  return (
    <svg viewBox="0 0 60 84" width="60" height="84" aria-hidden="true">
      <rect width="60" height="84" fill={paper} />
      {style === 'classic' && (
        <>
          <rect width="4" height="84" fill={c1} />
          <rect x="4" width="1.2" height="84" fill={c2} />
          {lines(12, 30, 26)}
          <rect x="12" y="72" width="36" height=".8" fill={ink} opacity=".3" />
        </>
      )}
      {style === 'centered' && (
        <>
          <rect x="4" y="4" width="52" height="76" fill="none" stroke={c1} strokeWidth="1" />
          <rect x="6.5" y="6.5" width="47" height="71" fill="none" stroke={c2} strokeWidth=".6" />
          {lines(30, 30, 28, 'middle')}
          <rect x="21" y="45" width="18" height=".8" fill={c1} />
          <rect x="28.4" y="43.6" width="3.2" height="3.2" fill={c2} transform="rotate(45 30 45.2)" />
        </>
      )}
      {style === 'bold' && (
        <>
          <defs>
            <linearGradient id={`g-${c1}-${c2}`} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor={c1} />
              <stop offset="1" stopColor={c2} />
            </linearGradient>
          </defs>
          <rect width="60" height="47" fill={`url(#g-${c1}-${c2})`} />
          <rect y="47" width="60" height="1.6" fill={c2} />
          <rect x="8" y="36" width="28" height="3.4" rx="1.7" fill="#fff" />
          <rect x="8" y="56" width="20" height="1.6" rx=".8" fill={ink} opacity=".35" />
        </>
      )}
      {style === 'minimal' && (
        <>
          <rect x="8" y="16" width="6" height="6" fill={c1} />
          <rect x="11" y="19" width="6" height="6" fill="none" stroke={c2} strokeWidth=".8" />
          {lines(8, 34, 30)}
          <rect x="8" y="30" width="8" height=".9" fill={c1} />
        </>
      )}
      {style === 'frame' && (
        <>
          <rect x="3" y="3" width="54" height="78" fill={c1} opacity=".16" stroke={c1} strokeWidth="2" />
          <rect x="7" y="7" width="46" height="70" fill="none" stroke={c2} strokeWidth=".6" />
          {lines(30, 32, 26, 'middle')}
        </>
      )}
    </svg>
  )
}

/** Look of the cover and back page: layout, colours and title font. */
export function DesignPicker({ design, onChange }: Props) {
  const preset = paletteIndex(design.color1, design.color2)
  return (
    <Section title="Cover and back page look" fold="open">
      <Field label="Layout">
        <div className="styles" role="radiogroup" aria-label="Cover layout">
          {STYLES.map((s) => (
            <label key={s.value} className={`style-tile${design.cover_style === s.value ? ' on' : ''}`} title={s.hint}>
              <input type="radio" name="cover-style" checked={design.cover_style === s.value} onChange={() => onChange({ cover_style: s.value })} />
              <Thumb style={s.value} c1={design.color1} c2={design.color2} />
              <span>{s.label}</span>
            </label>
          ))}
        </div>
      </Field>

      <Field label="Colours" note="A main colour and a lighter accent, mixed on the cover and back page.">
        <div className="swatches" role="radiogroup" aria-label="Colour pair">
          {PALETTES.map((p, i) => (
            <button
              key={p.name}
              type="button"
              role="radio"
              aria-checked={preset === i}
              aria-label={p.name}
              title={p.name}
              className={`swatch${preset === i ? ' on' : ''}`}
              style={{ background: `linear-gradient(135deg, ${p.c1} 50%, ${p.c2} 50%)` }}
              onClick={() => onChange({ color1: p.c1, color2: p.c2 })}
            />
          ))}
        </div>
        <div className="custom-colours">
          <label>
            <span>Main</span>
            <input type="color" value={isHex(design.color1) ? design.color1 : '#0a7556'} onChange={(e) => onChange({ color1: e.target.value })} />
          </label>
          <label>
            <span>Accent</span>
            <input type="color" value={isHex(design.color2) ? design.color2 : '#d9a441'} onChange={(e) => onChange({ color2: e.target.value })} />
          </label>
        </div>
      </Field>

      <Field label="Decoration" note="A small drawing in the empty space, in your two colours.">
        <select value={design.motif} onChange={(e) => onChange({ motif: e.target.value as Motif })}>
          {MOTIFS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Title font">
        <select value={design.heading_font} onChange={(e) => onChange({ heading_font: e.target.value as DesignOptions['heading_font'] })}>
          {FONT_CHOICES.map((f) => (
            <option key={f.key} value={f.key} style={{ fontFamily: f.stack }}>
              {f.label}
            </option>
          ))}
        </select>
        <p className="font-sample title" style={{ fontFamily: fontStack(design.heading_font) }}>
          Priya &amp; Arjun
        </p>
      </Field>
    </Section>
  )
}

/** Chat text font, with a sample line in that font. */
export function ChatFontField({ value, onChange }: { value: DesignOptions['heading_font']; onChange: (key: DesignOptions['heading_font']) => void }) {
  return (
    <Field label="Chat font" note="Letters that a font does not have, such as Hindi or emoji, are filled in automatically.">
      <select value={value} onChange={(e) => onChange(e.target.value as DesignOptions['heading_font'])}>
        {FONT_CHOICES.filter((f) => f.forChat).map((f) => (
          <option key={f.key} value={f.key} style={{ fontFamily: f.stack }}>
            {f.label} · {f.note}
          </option>
        ))}
      </select>
      <p className="font-sample" style={{ fontFamily: fontStack(value) }}>
        {SAMPLE_TEXT}
      </p>
    </Field>
  )
}