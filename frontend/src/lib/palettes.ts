/** Two-colour pairs for the cover and back page: a main colour and a lighter accent. */
export interface Palette {
  name: string
  c1: string
  c2: string
}

export const PALETTES: Palette[] = [
  { name: 'Forest and gold', c1: '#0a7556', c2: '#d9a441' },
  { name: 'Ocean', c1: '#0b5cad', c2: '#27b5c9' },
  { name: 'Sunset', c1: '#c2410c', c2: '#f5a623' },
  { name: 'Berry', c1: '#8e2a68', c2: '#f0a35e' },
  { name: 'Midnight and gold', c1: '#1f2a44', c2: '#c9a24a' },
  { name: 'Rose', c1: '#be185d', c2: '#f9a8c4' },
  { name: 'Lavender', c1: '#5b3fa6', c2: '#b9a4ec' },
  { name: 'Charcoal', c1: '#2b2f33', c2: '#9aa5ad' },
]

export const isHex = (v: string): boolean => /^#[0-9a-fA-F]{6}$/.test(v)

export function paletteIndex(c1: string, c2: string): number {
  return PALETTES.findIndex((p) => p.c1.toLowerCase() === c1.toLowerCase() && p.c2.toLowerCase() === c2.toLowerCase())
}