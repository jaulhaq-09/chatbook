import { describe, expect, it } from 'vitest'
import { describeError, expiryLabel, formatBytes, formatDay, formatRange, hourLabel, pagesLabel, plural, share } from './format'

describe('formatBytes', () => {
  it('scales units', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2.0 KB')
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB')
    expect(formatBytes(1.5 * 1024 ** 3)).toBe('1.5 GB')
    expect(formatBytes(250 * 1024 * 1024)).toBe('250 MB')
  })
})

describe('plural', () => {
  it('handles one and many', () => {
    expect(plural(1, 'photo')).toBe('1 photo')
    expect(plural(0, 'photo')).toBe('0 photos')
    expect(plural(12345, 'message')).toBe('12,345 messages')
  })
})

describe('formatRange', () => {
  it('omits the first year when both ends share it', () => {
    expect(formatRange('2026-03-12T08:58:00', '2026-04-18T07:46:00')).toBe('12 Mar – 18 Apr 2026')
  })
  it('keeps both years across a year boundary', () => {
    expect(formatRange('2025-12-30T10:00:00', '2026-01-02T10:00:00')).toBe('30 Dec 2025 – 2 Jan 2026')
  })
  it('shows a single day once', () => {
    expect(formatRange('2026-03-12T08:00:00', '2026-03-12T20:00:00')).toBe('12 Mar 2026')
  })
})

describe('describeError', () => {
  it('passes strings through', () => {
    expect(describeError('Nope')).toBe('Nope')
  })
  it('reads the first validation error', () => {
    expect(describeError([{ loc: ['body', 'album', 'columns'], msg: 'Input should be less than or equal to 4' }])).toBe(
      'album.columns: Input should be less than or equal to 4',
    )
  })
  it('has a fallback', () => {
    expect(describeError(undefined)).toMatch(/Something went wrong/)
  })
})

describe('expiryLabel', () => {
  it('falls back for bad input', () => {
    expect(expiryLabel('garbage')).toBe('Deleted automatically after a day')
  })
  it('mentions a time for good input', () => {
    expect(expiryLabel('2026-10-19T17:12:00+00:00')).toMatch(/^Deleted automatically at \d{1,2}:\d{2} (am|pm)$/)
  })
})

describe('pagesLabel', () => {
  it('reads naturally', () => {
    expect(pagesLabel(1)).toBe('about 1 page')
    expect(pagesLabel(120)).toBe('about 120 pages')
  })
})

describe('formatDay', () => {
  it('names the weekday without shifting the date', () => {
    expect(formatDay('2026-03-02')).toBe('Mon 2 Mar 2026')
    expect(formatDay('2026-03-02T23:59:00')).toBe('Mon 2 Mar 2026')
  })
})

describe('hourLabel', () => {
  it('uses a 12 hour clock', () => {
    expect([0, 9, 12, 13, 23].map(hourLabel)).toEqual(['12 am', '9 am', '12 pm', '1 pm', '11 pm'])
  })
})

describe('share', () => {
  it('rounds and survives zero', () => {
    expect(share(1, 3)).toBe(33)
    expect(share(5, 0)).toBe(0)
  })
})