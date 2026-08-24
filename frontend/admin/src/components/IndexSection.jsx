import { useState } from 'react'
import { apiJson } from '../lib/api.js'
import Section, { btnGreen } from './Section.jsx'

export default function IndexSection() {
  const [status, setStatus] = useState('')

  const run = async () => {
    setStatus('Building vector + BM25 indexes… this can take a minute.')
    try {
      const data = await apiJson('/api/rag-index', { method: 'POST' })
      setStatus(`Indexed ${data.indexed} bars.`)
    } catch (e) {
      setStatus(`Error: ${e.message}`)
    }
  }

  return (
    <Section n={6} title="Build search index" note="Rebuilds the vector + BM25 index from current database content. Run after collecting or enriching new bars.">
      <button className={btnGreen} onClick={run}>Index bars</button>
      {status && <div className="text-sm text-gray-600 mt-2">{status}</div>}
    </Section>
  )
}
