import { useState } from 'react'
import { api, apiJson } from '../lib/api.js'
import Section, { btnBlue, btnGray, inputCls } from './Section.jsx'

export default function CollectSection({ neighborhood, setNeighborhood, neighborhoods, onCollected }) {
  const [status, setStatus] = useState('')
  const [rows, setRows] = useState(null)

  const run = async () => {
    setStatus(`Running collection for ${neighborhood}… this can take a minute or two.`)
    setRows(null)
    try {
      const data = await apiJson('/api/collect', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ neighborhood }),
      })
      setStatus('Done.')
      setRows(Object.entries(data.results))
      onCollected?.()
    } catch (e) {
      setStatus(`Error: ${e.message}`)
    }
  }

  const exportCsv = async () => {
    try {
      const res = await api(`/api/export?neighborhood=${encodeURIComponent(neighborhood)}`)
      if (!res.ok) { setStatus('Export failed.'); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bacaro_hop_${neighborhood.replace(/ /g, '_')}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setStatus(e.message)
    }
  }

  return (
    <Section n={2} title="Collect bars">
      <label className="block text-sm text-gray-600 mb-1">Sestiere</label>
      <select value={neighborhood} onChange={(e) => setNeighborhood(e.target.value)} className={inputCls}>
        {neighborhoods.map((n) => <option key={n} value={n}>{n}</option>)}
      </select>
      <div>
        <button className={btnBlue} onClick={run}>Run collection</button>
        <button className={btnGray} onClick={() => onCollected?.()}>Refresh summary</button>
        <button className={btnGray} onClick={exportCsv}>Export CSV</button>
      </div>
      {status && <div className="text-sm text-gray-600 mt-2">{status}</div>}
      {rows && (
        <div className="mt-2">
          {rows.map(([name, s]) => (
            <div key={name} className="flex justify-between text-sm py-1.5 border-b border-gray-100 last:border-0">
              <span className="font-semibold">{name}</span>
              <span className="text-gray-500">{s.saved} saved ({s.candidates} found, {s.skipped_non_bar_type} not a bar type)</span>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
