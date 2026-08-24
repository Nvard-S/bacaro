import { describe, it, expect } from 'vitest'
import { highlightSegments } from '../../lib/highlight.js'

describe('highlightSegments', () => {
  it('returns the whole text when there are no terms', () => {
    expect(highlightSegments('hello', [], '')).toEqual([{ text: 'hello', kind: null }])
  })

  it('marks a bar-name match', () => {
    expect(highlightSegments('Try Vino Vero today', ['Vino Vero'], '')).toEqual([
      { text: 'Try ', kind: null },
      { text: 'Vino Vero', kind: 'name' },
      { text: ' today', kind: null },
    ])
  })

  it('marks the query case-insensitively', () => {
    const segs = highlightSegments('good WINE here', [], 'wine')
    expect(segs.find((s) => s.kind === 'query').text).toBe('WINE')
  })

  it('prefers the longer term when two overlap at the same spot', () => {
    expect(highlightSegments('Bacaro Vero', ['Bacaro Vero'], 'Bacaro')).toEqual([
      { text: 'Bacaro Vero', kind: 'name' },
    ])
  })
})
