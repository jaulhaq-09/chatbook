import { useId, type ReactNode } from 'react'

interface SegmentedProps<T extends string | number> {
  label: string
  value: T
  options: { value: T; label: string; hint?: string }[]
  onChange: (value: T) => void
}

/** A single-choice control. Rendered as a radio group so it works with the keyboard and screen readers. */
export function Segmented<T extends string | number>({ label, value, options, onChange }: SegmentedProps<T>) {
  const name = useId()
  return (
    <div className="seg" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <label key={String(o.value)} className={o.value === value ? 'on' : ''} title={o.hint}>
          <input
            type="radio"
            name={name}
            checked={o.value === value}
            onChange={() => onChange(o.value)}
          />
          <span>{o.label}</span>
        </label>
      ))}
    </div>
  )
}

interface SwitchProps {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  hint?: string
  disabled?: boolean
}

export function Switch({ label, checked, onChange, hint, disabled }: SwitchProps) {
  return (
    <label className={`switch${disabled ? ' disabled' : ''}`}>
      <span className="switch-text">
        {label}
        {hint && <small>{hint}</small>}
      </span>
      <input type="checkbox" role="switch" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <i aria-hidden="true" />
    </label>
  )
}

export function Field({ label, children, note }: { label: string; children: ReactNode; note?: string }) {
  const id = useId()
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div id={id}>{children}</div>
      {note && <p className="note">{note}</p>}
    </div>
  )
}

/**
 * A titled group of settings. With `fold`, the group opens and closes, which keeps a long settings list
 * short: the person opens only what they want to change.
 */
export function Section({
  title,
  children,
  aside,
  fold,
}: {
  title: string
  children: ReactNode
  aside?: ReactNode
  fold?: 'open' | 'closed'
}) {
  if (fold) {
    return (
      <details className="section fold" open={fold === 'open'}>
        <summary>
          <h3>{title}</h3>
          {aside}
          <svg className="fold-chev" viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
            <path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </summary>
        <div className="section-body">{children}</div>
      </details>
    )
  }
  return (
    <section className="section">
      <header>
        <h3>{title}</h3>
        {aside}
      </header>
      <div className="section-body">{children}</div>
    </section>
  )
}

export function Spinner({ small }: { small?: boolean }) {
  return <span className={`spinner${small ? ' small' : ''}`} role="status" aria-label="Loading" />
}

export function Icon({ name }: { name: 'sun' | 'moon' | 'auto' | 'upload' | 'file' | 'x' | 'download' | 'open' | 'plus' | 'check' | 'chev-l' | 'chev-r' }) {
  const p = {
    width: 18,
    height: 18,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
  }
  switch (name) {
    case 'sun':
      return (
        <svg {...p}>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      )
    case 'moon':
      return (
        <svg {...p}>
          <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
        </svg>
      )
    case 'auto':
      return (
        <svg {...p}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3v18" />
          <path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none" />
        </svg>
      )
    case 'upload':
      return (
        <svg {...p}>
          <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
        </svg>
      )
    case 'file':
      return (
        <svg {...p}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5" />
        </svg>
      )
    case 'x':
      return (
        <svg {...p}>
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      )
    case 'download':
      return (
        <svg {...p}>
          <path d="M12 4v12M7 11l5 5 5-5M4 20h16" />
        </svg>
      )
    case 'open':
      return (
        <svg {...p}>
          <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
        </svg>
      )
    case 'plus':
      return (
        <svg {...p}>
          <path d="M12 5v14M5 12h14" />
        </svg>
      )
    case 'check':
      return (
        <svg {...p}>
          <path d="M5 12.5l4.5 4.5L19 7" />
        </svg>
      )
    case 'chev-l':
      return (
        <svg {...p}>
          <path d="M15 6l-6 6 6 6" />
        </svg>
      )
    case 'chev-r':
      return (
        <svg {...p}>
          <path d="M9 6l6 6-6 6" />
        </svg>
      )
  }
}