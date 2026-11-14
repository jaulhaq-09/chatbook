import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { pdfjs, type PDFDocumentProxy } from '../lib/pdf'
import { clampPage, GRID_GAP, optionFor, singleWidth, tileWidth, type ViewMode } from '../lib/views'
import { Icon, Spinner } from './ui'

interface Props {
  data: ArrayBuffer | null
  mode: ViewMode
  onMode: (mode: ViewMode) => void
  /** Reports how many pages the section has, once it is loaded. */
  onPages?: (count: number) => void
  /** Asks the viewer to show the start or the end of the section, e.g. the cover or the back page. */
  jump?: Jump | null
}

export interface Jump {
  to: 'first' | 'last'
  /** Changes with every request, so asking twice for the same place works. */
  token: number
  /** True when the pages on screen are already the right section. Otherwise wait for the new pages. */
  immediate: boolean
}

/** One printed page drawn on a canvas. It only renders while it is near the screen, so a long section stays light. */
function PageCanvas({ doc, number, width, aspect }: { doc: PDFDocumentProxy; number: number; width: number; aspect: number }) {
  const holder = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const [near, setNear] = useState(false)
  const [drawn, setDrawn] = useState(false)

  useEffect(() => {
    const el = holder.current
    if (!el) return
    const io = new IntersectionObserver((entries) => setNear(entries.some((e) => e.isIntersecting)), { rootMargin: '700px 0px' })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    if (!near || width <= 0) return
    const target = canvas.current
    if (!target) return
    let cancelled = false
    let task: { cancel: () => void; promise: Promise<unknown> } | null = null
    void doc.getPage(number).then((page) => {
      if (cancelled) return
      const base = page.getViewport({ scale: 1 })
      const ratio = Math.min(2, window.devicePixelRatio || 1)
      const viewport = page.getViewport({ scale: (width * ratio) / base.width })
      target.width = Math.floor(viewport.width)
      target.height = Math.floor(viewport.height)
      const context = target.getContext('2d')
      if (!context) return
      task = page.render({ canvasContext: context, viewport })
      task.promise.then(() => !cancelled && setDrawn(true)).catch(() => undefined) // a cancelled render rejects on purpose
    })
    return () => {
      cancelled = true
      task?.cancel()
    }
  }, [doc, number, width, near])

  return (
    <div ref={holder} className={`sheet${drawn ? '' : ' blank'}`} style={{ width, height: Math.round(width * aspect) }}>
      <canvas ref={canvas} aria-label={`Page ${number}`} role="img" />
    </div>
  )
}

export function PageViewer({ data, mode, onMode, onPages, jump }: Props) {
  const area = useRef<HTMLDivElement>(null)
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null)
  const docRef = useRef<PDFDocumentProxy | null>(null)
  const [aspect, setAspect] = useState(1.414)
  const [size, setSize] = useState({ w: 0, h: 0 })
  const [current, setCurrent] = useState(1)
  const [broken, setBroken] = useState(false)
  const option = optionFor(mode)

  // Measure the scrolling area, minus its padding.
  useLayoutEffect(() => {
    const el = area.current
    if (!el) return
    const measure = () => {
      const cs = getComputedStyle(el)
      const px = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)
      const py = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)
      setSize({ w: Math.max(0, el.clientWidth - px), h: Math.max(0, el.clientHeight - py) })
    }
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    measure()
    return () => ro.disconnect()
  }, [])

  // Load the PDF. The old document stays until the new one is ready.
  useEffect(() => {
    if (!data) {
      setDoc(null)
      return
    }
    let cancelled = false
    let settled = false
    // pdf.js takes ownership of the bytes it is given, so hand it a copy.
    const task = pdfjs.getDocument({ data: new Uint8Array(data.slice(0)) })
    task.promise
      .then(async (loaded) => {
        settled = true
        if (cancelled) {
          void loaded.destroy()
          return
        }
        const first = await loaded.getPage(1)
        const v = first.getViewport({ scale: 1 })
        if (cancelled) {
          void loaded.destroy()
          return
        }
        setAspect(v.height / v.width)
        const previous = docRef.current
        docRef.current = loaded
        setDoc(loaded)
        setBroken(false)
        setCurrent((c) => clampPage(c, loaded.numPages))
        onPages?.(loaded.numPages)
        if (previous) void previous.destroy()
      })
      .catch(() => {
        settled = true
        if (!cancelled) setBroken(true)
      })
    return () => {
      cancelled = true
      if (!settled) void task.destroy()
    }
  }, [data, onPages])

  useEffect(
    () => () => {
      void docRef.current?.destroy()
    },
    [],
  )

  const count = doc?.numPages ?? 0
  const go = useCallback((page: number) => setCurrent(clampPage(page, count)), [count])

  // Show the cover or the back page when asked. If the section is about to change, wait for its pages.
  const pending = useRef<'first' | 'last' | null>(null)
  const apply = useCallback(
    (to: 'first' | 'last', pages: number) => {
      setCurrent(to === 'first' ? 1 : pages)
      requestAnimationFrame(() => requestAnimationFrame(() => area.current?.scrollTo({ top: to === 'first' ? 0 : area.current.scrollHeight })))
    },
    [],
  )
  useEffect(() => {
    if (!jump) return
    if (jump.immediate && count > 0) apply(jump.to, count)
    else pending.current = jump.to
    // Only a new request matters here, not changes of the page count.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jump?.token])
  useEffect(() => {
    if (doc && pending.current) {
      apply(pending.current, doc.numPages)
      pending.current = null
    }
  }, [doc, apply])

  const onKey = (e: React.KeyboardEvent) => {
    if (mode !== 'single') return
    const keys: Record<string, number> = { ArrowRight: current + 1, ArrowDown: current + 1, PageDown: current + 1, ArrowLeft: current - 1, ArrowUp: current - 1, PageUp: current - 1, Home: 1, End: count }
    if (e.key in keys) {
      e.preventDefault()
      go(keys[e.key])
    }
  }

  if (broken) {
    return (
      <div className="viewer" ref={area}>
        <p className="note error" role="alert">
          The pages could not be shown. Try changing a setting, or make the PDF and open it directly.
        </p>
      </div>
    )
  }

  return (
    <div className={`viewer${mode === 'single' ? ' is-single' : ''}`} ref={area} tabIndex={0} onKeyDown={onKey} aria-label={`Pages, ${option.label.toLowerCase()}`}>
      {!doc && (
        <div className="stage-empty">
          <Spinner />
        </div>
      )}

      {doc && mode !== 'single' && (
        <div className="grid" style={{ gap: GRID_GAP }}>
          {Array.from({ length: count }, (_, i) => i + 1).map((n) => {
            const w = tileWidth(size.w, option.columns)
            return (
              <button
                type="button"
                className="tile"
                key={n}
                onClick={() => {
                  setCurrent(n)
                  onMode('single')
                }}
                title={`Open page ${n}`}
              >
                <PageCanvas doc={doc} number={n} width={w} aspect={aspect} />
                <span className="tile-label">{n}</span>
              </button>
            )
          })}
        </div>
      )}

      {doc && mode === 'single' && (
        <div className="single">
          <div className="single-bar">
            <button type="button" className="btn ghost" onClick={() => onMode('m')}>
              All pages
            </button>
            <div className="pager">
              <button type="button" className="icon-btn" disabled={current <= 1} onClick={() => go(current - 1)} aria-label="Previous page">
                <Icon name="chev-l" />
              </button>
              <label className="pageinput">
                <input type="number" min={1} max={count} value={current} onChange={(e) => go(Number(e.target.value))} aria-label="Page number" />
                <span>of {count}</span>
              </label>
              <button type="button" className="icon-btn" disabled={current >= count} onClick={() => go(current + 1)} aria-label="Next page">
                <Icon name="chev-r" />
              </button>
            </div>
          </div>
          <PageCanvas doc={doc} number={current} width={singleWidth(size.w, Math.max(200, size.h - 64), aspect)} aspect={aspect} />
        </div>
      )}
    </div>
  )
}