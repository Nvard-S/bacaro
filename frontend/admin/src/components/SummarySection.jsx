import { useEffect, useState } from 'react'
import { apiJson } from '../lib/api.js'
import Section from './Section.jsx'

const CARDS = [
  ['Total bars', 'total'],
  ['Avg rating', 'avg_rating'],
  ['With website', 'with_website'],
  ['With reviews', 'with_reviews'],
  ['With coordinates', 'with_coordinates'],
]

export default function SummarySection({ neighborhood, refreshKey }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    apiJson(`/api/summary?neighborhood=${encodeURIComponent(neighborhood)}`)
      .then(setData)
      .catch(() => {})
  }, [neighborhood, refreshKey])

  return (
    <Section n={8} title="Summary">
      <div className="grid grid-cols-2 gap-2.5">
        {CARDS.map(([label, key]) => (
          <div key={key} className="bg-gray-50 rounded p-2.5 text-sm">
            {label}
            <span className="block text-2xl font-semibold">{data ? (data[key] ?? '–') : '–'}</span>
          </div>
        ))}
      </div>
    </Section>
  )
}
