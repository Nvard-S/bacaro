import { useEffect, useState } from 'react'
import { apiJson } from '../lib/api.js'
import Section from './Section.jsx'

const ITEMS = [
  ['Google Places', '/api/settings'],
  ['Parallel', '/api/settings/parallel'],
  ['OpenAI', '/api/settings/openai'],
]

export default function SettingsStatus() {
  const [status, setStatus] = useState({})

  useEffect(() => {
    ITEMS.forEach(([label, path]) => {
      apiJson(path)
        .then((d) => setStatus((s) => ({ ...s, [label]: d })))
        .catch(() => {})
    })
  }, [])

  return (
    <Section n={1} title="API keys" note="Keys come from environment variables, not this UI. Status just confirms each is loaded.">
      {ITEMS.map(([label]) => {
        const d = status[label]
        const text = !d ? '…' : d.has_key ? `loaded (${d.masked_key})` : 'not set in environment'
        return <div key={label} className="text-sm text-gray-600">{label}: {text}</div>
      })}
    </Section>
  )
}
