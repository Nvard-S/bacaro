import { useState } from 'react'
import { apiJson } from '../lib/api.js'
import Section, { btnBlue, inputCls } from './Section.jsx'

export default function SearchSection({ neighborhoods }) {
  const [query, setQuery] = useState('')
  const [neighborhood, setNeighborhood] = useState('All Venice')
  const [topN, setTopN] = useState(5)
  const [status, setStatus] = useState('')
  const [result, setResult] = useState(null)

  const run = async () => {
    if (!query.trim()) { setStatus('Enter a search query first.'); return }
    setStatus('Searching…')
    setResult(null)
    try {
      const data = await apiJson('/api/rag-search', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, neighborhood, top_n: Number(topN) }),
      })
      setStatus('')
      setResult(data)
    } catch (e) {
      setStatus(`Error: ${e.message}`)
    }
  }

  return (
    <Section n={7} title="Search">
      <label className="block text-sm text-gray-600 mb-1">Question</label>
      <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && run()}
        placeholder="e.g. Where can I get good cicchetti near Rialto?" className={inputCls} />
      <label className="block text-sm text-gray-600 mb-1">Sestiere</label>
      <select value={neighborhood} onChange={(e) => setNeighborhood(e.target.value)} className={inputCls}>
        {neighborhoods.map((n) => <option key={n} value={n}>{n}</option>)}
      </select>
      <label className="block text-sm text-gray-600 mb-1">Top results</label>
      <input type="number" min="1" max="20" value={topN} onChange={(e) => setTopN(e.target.value)}
        className="w-24 mb-2.5 px-2.5 py-2 border border-gray-300 rounded text-sm" />
      <div><button className={btnBlue} onClick={run}>Search</button></div>
      {status && <div className="text-sm text-gray-600 mt-2">{status}</div>}
      {result && (
        <div className="mt-3">
          <div className="text-sm text-gray-500 mb-2">Analyzed {result.analyzed} bars.</div>
          <div className="bg-gray-50 rounded p-3 font-semibold mb-3">{result.answer}</div>
          {(result.sources || []).map((s) => (
            <div key={s.place_id} className={'border-l-4 pl-3 py-2 mb-2 text-sm ' + (s.confirmed ? 'border-blue-600' : 'border-gray-300')}>
              <span className="font-bold">{s.name}</span>
              <span className="text-gray-500"> — {s.neighborhood} (rating {s.rating ?? '–'})</span>
              {!s.confirmed && <span className="ml-2 text-xs bg-gray-200 rounded px-1.5 py-0.5">Not confirmed</span>}
              {s.explanation && <div className="mt-1">{s.explanation}</div>}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
