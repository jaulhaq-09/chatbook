import { describe, expect, it } from 'vitest'
import type { Job } from '../api/types'
import { DEFAULT_OPTIONS, defaultMe, loadOptions, pickRemembered, reconcileOptions, volumeUnit } from './options'

const job = (names: string[]): Job =>
  ({
    senders: names.map((name, i) => ({ name, count: 100 - i })),
  }) as Job

describe('defaultMe', () => {
  it('picks the second most active person', () => {
    expect(defaultMe(job(['Priya', 'Arjun']))).toBe('Arjun')
  })
  it('falls back to the only person, or nobody', () => {
    expect(defaultMe(job(['Solo']))).toBe('Solo')
    expect(defaultMe(job([]))).toBeNull()
  })
})

describe('reconcileOptions', () => {
  it('fills in the right-hand person', () => {
    expect(reconcileOptions(DEFAULT_OPTIONS, job(['A', 'B'])).me).toBe('B')
  })
  it('keeps a valid choice and returns the same object when nothing changes', () => {
    const chosen = { ...DEFAULT_OPTIONS, me: 'A' }
    expect(reconcileOptions(chosen, job(['A', 'B']))).toBe(chosen)
  })
  it('drops people who are not in the new chat', () => {
    const o = { ...DEFAULT_OPTIONS, me: 'Gone', exclude_people: ['Gone', 'B'] }
    const next = reconcileOptions(o, job(['A', 'B']))
    expect(next.me).toBe('B')
    expect(next.exclude_people).toEqual(['B'])
  })
})

describe('volumeUnit', () => {
  it('names what a volume holds', () => {
    expect(volumeUnit('book')).toBe('messages')
    expect(volumeUnit('album')).toBe('photos')
  })
})

describe('remembered options', () => {
  it('keeps layout choices and leaves chat-specific ones out', () => {
    const saved = pickRemembered({ ...DEFAULT_OPTIONS, page_size: 'A5', me: 'Priya', query: 'secret', exclude_people: ['X'] })
    expect(saved).toMatchObject({ page_size: 'A5' })
    expect(saved).not.toHaveProperty('me')
    expect(saved).not.toHaveProperty('query')
    expect(saved).not.toHaveProperty('exclude_people')
  })
  it('loads saved choices over the defaults', () => {
    const o = loadOptions(JSON.stringify({ page_size: 'Letter', text_size: 'l', album: { columns: 2 } }))
    expect(o.page_size).toBe('Letter')
    expect(o.text_size).toBe('l')
    expect(o.album.columns).toBe(2)
    expect(o.album.paper).toBe('white') // untouched album fields keep their defaults
  })
  it('ignores junk and wrongly typed values', () => {
    expect(loadOptions('not json')).toEqual(DEFAULT_OPTIONS)
    expect(loadOptions(JSON.stringify({ page_size: 7, cover: 'yes' }))).toEqual(DEFAULT_OPTIONS)
    expect(loadOptions(null)).toEqual(DEFAULT_OPTIONS)
  })
})

describe('background picture settings', () => {
  it('start faint and on every page', () => {
    expect(DEFAULT_OPTIONS.background).toEqual({ enabled: true, fit: 'cover', opacity: 0.3, scope: 'all' })
  })

  it('are remembered, with missing fields filled from the defaults', () => {
    const o = loadOptions(JSON.stringify({ background: { opacity: 0.6, fit: 'tile' } }))
    expect(o.background).toEqual({ enabled: true, fit: 'tile', opacity: 0.6, scope: 'all' })
    expect(pickRemembered(o)).toHaveProperty('background')
  })
})

describe('cover, back page and font settings', () => {
  it('start with the classic cover, a back page and the modern font', () => {
    expect(DEFAULT_OPTIONS.design.cover_style).toBe('classic')
    expect(DEFAULT_OPTIONS.back).toMatchObject({ enabled: true, heading: 'The end' })
    expect(DEFAULT_OPTIONS.chat_font).toBe('sans')
  })

  it('remember the look but not the words, which belong to one chat', () => {
    const o = loadOptions(
      JSON.stringify({
        chat_font: 'serif',
        design: { cover_style: 'bold', color1: '#112233' },
        cover_text: { tagline: 'For Mahi' },
        back: { message: 'Thanks' },
        header_left: 'Hello',
      }),
    )
    expect(o.chat_font).toBe('serif')
    expect(o.design).toEqual({ cover_style: 'bold', color1: '#112233', color2: '#d9a441', heading_font: 'serif', motif: 'bubbles' })
    expect(o.cover_text.tagline).toBe('')
    expect(o.back.message).toBe('')
    expect(o.header_left).toBe('')
  })
})