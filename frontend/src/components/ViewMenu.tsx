import { useEffect, useId, useRef, useState } from 'react'
import { optionFor, VIEW_OPTIONS, type ViewMode } from '../lib/views'

interface Props {
  mode: ViewMode
  onChange: (mode: ViewMode) => void
}

/** A small picture of each layout: as many boxes as pages per row. */
function Glyph({ columns }: { columns: number }) {
  if (columns === 0) {
    return (
      <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
        <rect x="5" y="2" width="10" height="16" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    )
  }
  const cols = Math.min(columns, 4)
  const rows = columns === 1 ? 1 : 2
  const w = 16 / cols - 1.5
  const h = columns === 1 ? 16 : 7
  const boxes = []
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      boxes.push(<rect key={`${r}-${c}`} x={2 + c * (16 / cols)} y={2 + r * 9} width={columns === 1 ? 10 : w} height={h} rx="1" fill="none" stroke="currentColor" strokeWidth="1.4" transform={columns === 1 ? 'translate(3 0)' : undefined} />)
    }
  }
  return (
    <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
      {boxes}
    </svg>
  )
}

export function ViewMenu({ mode, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const menuId = useId()
  const current = optionFor(mode)

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

  const move = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const items = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>('[role=menuitemradio]'))
    const at = items.indexOf(document.activeElement as HTMLButtonElement)
    const next = e.key === 'ArrowDown' ? (at + 1) % items.length : (at - 1 + items.length) % items.length
    items[next]?.focus()
  }

  return (
    <div className="viewmenu" ref={root}>
      <button type="button" className="btn view-btn" aria-haspopup="menu" aria-expanded={open} aria-controls={menuId} onClick={() => setOpen((o) => !o)}>
        <Glyph columns={current.columns} />
        <span>View</span>
        <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true">
          <path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="menu" id={menuId} role="menu" aria-label="View" onKeyDown={move}>
          {VIEW_OPTIONS.map((o, i) => (
            <div key={o.id}>
              {o.id === 'single' && <hr />}
              <button
                type="button"
                role="menuitemradio"
                aria-checked={o.id === mode}
                className={o.id === mode ? 'on' : ''}
                autoFocus={o.id === mode || (i === 0 && mode === 'single')}
                title={o.hint}
                onClick={() => {
                  onChange(o.id)
                  setOpen(false)
                }}
              >
                <i aria-hidden="true">{o.id === mode ? '•' : ''}</i>
                <Glyph columns={o.columns} />
                <span>{o.label}</span>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}