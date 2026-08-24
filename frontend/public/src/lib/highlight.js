// Split answer text into segments, marking spans that match a bar name
// ('name') or the user's query ('query'), longest term first, so the UI can
// style them. Pure + case-insensitive so it's easy to unit-test.
export function highlightSegments(text, names = [], query = '') {
  const terms = [
    ...names.filter(Boolean).map((t) => ({ term: t, kind: 'name' })),
    ...(query ? [{ term: query, kind: 'query' }] : []),
  ].sort((a, b) => b.term.length - a.term.length)

  if (!terms.length || !text) return [{ text: text || '', kind: null }]

  const segments = []
  let rest = text
  while (rest.length) {
    let best = null
    for (const { term, kind } of terms) {
      const idx = rest.toLowerCase().indexOf(term.toLowerCase())
      if (idx === -1) continue
      if (best === null || idx < best.idx || (idx === best.idx && term.length > best.len)) {
        best = { idx, len: term.length, kind }
      }
    }
    if (!best) {
      segments.push({ text: rest, kind: null })
      break
    }
    if (best.idx > 0) segments.push({ text: rest.slice(0, best.idx), kind: null })
    segments.push({ text: rest.slice(best.idx, best.idx + best.len), kind: best.kind })
    rest = rest.slice(best.idx + best.len)
  }
  return segments
}
