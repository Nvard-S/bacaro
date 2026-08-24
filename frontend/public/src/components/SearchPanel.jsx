import { useState } from 'react'
import { useTypewriter } from '../hooks/useTypewriter.js'

const PLACEHOLDERS = [
  'near Rialto', 'baccalà mantecato', 'cheap wine bar', 'sarde in saor',
  'open late tonight', 'vegan cicchetti', 'local favorite spot',
]

export default function SearchPanel({
  query, onQueryChange, neighborhood, onNeighborhoodChange, onSearch, neighborhoods,
}) {
  const [focused, setFocused] = useState(false)
  const typed = useTypewriter(PLACEHOLDERS, focused || query.length > 0)

  return (
    <div className="flex flex-wrap gap-2.5 mb-4">
      <input
          type="text"
          aria-label="Search cicchetti bars"
          value={query}
          placeholder={typed}
          onChange={(e) => onQueryChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => { if (e.key === 'Enter') onSearch() }}
          className="flex-1 min-w-[220px] px-4 py-3 rounded-xl border-[1.5px] border-line bg-card text-ink text-base outline-none focus:border-teal"
        />
        <select
          aria-label="Neighborhood"
          value={neighborhood}
          onChange={(e) => onNeighborhoodChange(e.target.value)}
          className="px-3.5 py-3 rounded-xl border-[1.5px] border-line bg-card text-ink text-[0.95rem] outline-none focus:border-teal"
        >
          {neighborhoods.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <button
          type="button"
          onClick={onSearch}
          className="rounded-xl px-6 py-3 font-bold text-white bg-coral hover:bg-coral-strong active:translate-y-px transition"
      >
        Find bacari
      </button>
    </div>
  )
}
