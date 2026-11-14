/** How the preview shows the printed pages, in the spirit of the Windows Explorer "View" menu. */

export type ViewMode = 'xl' | 'l' | 'm' | 's' | 'xs' | 'single'

export interface ViewOption {
  id: ViewMode
  label: string
  hint: string
  /** Pages per row in the grid; 0 for the one-page reader. */
  columns: number
}

export const VIEW_OPTIONS: ViewOption[] = [
  { id: 'xl', label: 'Extra large pages', hint: 'One page per row, easy to read', columns: 1 },
  { id: 'l', label: 'Large pages', hint: 'Two pages per row', columns: 2 },
  { id: 'm', label: 'Medium pages', hint: 'Three pages per row', columns: 3 },
  { id: 's', label: 'Small pages', hint: 'Five pages per row', columns: 5 },
  { id: 'xs', label: 'Tiny pages', hint: 'Eight pages per row, see the whole section at once', columns: 8 },
  { id: 'single', label: 'One page at a time', hint: 'Arrow keys turn the page', columns: 0 },
]

const KEY = 'chatbook.view'
export const DEFAULT_VIEW: ViewMode = 'xl'

export function isViewMode(v: unknown): v is ViewMode {
  return typeof v === 'string' && VIEW_OPTIONS.some((o) => o.id === v)
}

export function loadView(): ViewMode {
  try {
    const v = localStorage.getItem(KEY)
    if (isViewMode(v)) return v
  } catch {
    /* storage can be blocked */
  }
  return DEFAULT_VIEW
}

export function saveView(v: ViewMode): void {
  try {
    localStorage.setItem(KEY, v)
  } catch {
    /* ignore */
  }
}

export function optionFor(mode: ViewMode): ViewOption {
  return VIEW_OPTIONS.find((o) => o.id === mode) ?? VIEW_OPTIONS[0]
}

export const GRID_GAP = 16
/** Pages never get wider than this, even on a very wide screen. */
export const MAX_PAGE_WIDTH = 920

/** Width of one page in a grid of `columns`, given the width of the area. */
export function tileWidth(areaWidth: number, columns: number): number {
  if (areaWidth <= 0 || columns <= 0) return 0
  const raw = Math.floor((areaWidth - GRID_GAP * (columns - 1)) / columns)
  return Math.max(40, Math.min(raw, MAX_PAGE_WIDTH))
}

/** Width of the page in the one-page reader: as large as fits both ways. */
export function singleWidth(areaWidth: number, areaHeight: number, aspect: number): number {
  if (areaWidth <= 0 || areaHeight <= 0 || aspect <= 0) return 0
  return Math.max(120, Math.floor(Math.min(areaWidth, areaHeight / aspect, MAX_PAGE_WIDTH * 1.4)))
}

export function clampPage(page: number, count: number): number {
  if (count <= 0) return 1
  return Math.min(Math.max(1, Math.round(page) || 1), count)
}