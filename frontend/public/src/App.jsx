import { useCallback, useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import Hero from './components/Hero.jsx'
import SearchPanel from './components/SearchPanel.jsx'
import TagChips from './components/TagChips.jsx'
import AnswerBanner from './components/AnswerBanner.jsx'
import ResultsGrid from './components/ResultsGrid.jsx'
import CrostinoLoader from './components/CrostinoLoader.jsx'
import { fetchTags, browse } from './api.js'
import { useDarkMode } from './hooks/useDarkMode.js'

const NEIGHBORHOODS = ['All Venice', 'Cannaregio', 'Castello', 'San Marco', 'Dorsoduro', 'San Polo', 'Santa Croce']

function buildRecap(query, neighborhood, tagSlugs, tagLabelMap) {
  const parts = [query ? `Looking for "${query}"` : 'Showing bacari']
  if (neighborhood && neighborhood !== 'All Venice') parts.push(`in ${neighborhood}`)
  if (tagSlugs.length) {
    parts.push(`tagged ${tagSlugs.map((s) => tagLabelMap[s] || s.replace(/_/g, ' ')).join(' and ')}`)
  }
  return parts.join(' ')
}

export default function App() {
  const { theme, toggle } = useDarkMode()
  const [tags, setTags] = useState([])
  const [tagLabelMap, setTagLabelMap] = useState({})
  const [selectedTags, setSelectedTags] = useState(() => new Set())
  const [query, setQuery] = useState('')
  const [neighborhood, setNeighborhood] = useState('All Venice')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    fetchTags()
      .then((t) => {
        setTags(t)
        setTagLabelMap(Object.fromEntries(t.map((x) => [x.slug, x.label])))
      })
      .catch(() => {})
  }, [])

  const runSearch = useCallback((q, nb, tagSlugs) => {
    setLoading(true)
    setError('')
    return browse({ query: q.trim(), neighborhood: nb, tags: tagSlugs, topN: 9 })
      .then((data) => {
        if (data.mode === 'search') {
          const scope = []
          if (data.neighborhood && data.neighborhood !== 'All Venice') scope.push(`in ${data.neighborhood}`)
          if (data.geo_filter_applied) scope.push(`within 1 km of ${data.location_detected}`)
          setResult({
            mode: 'search',
            answer: data.answer,
            items: data.sources || [],
            names: (data.sources || []).map((s) => s.name),
            status: `Analyzed ${data.analyzed} bar${data.analyzed === 1 ? '' : 's'}${scope.length ? ' ' + scope.join(', ') : ''}.`,
            query: q.trim(),
          })
        } else {
          setResult({
            mode: 'browse',
            items: data.bars || [],
            status: data.total > data.bars.length
              ? `Showing top ${data.bars.length} of ${data.total} bars, sorted by rating.`
              : `${data.total} bar${data.total === 1 ? '' : 's'} found.`,
          })
        }
      })
      .catch((e) => {
        setError(e.message)
        setResult(null)
      })
      .finally(() => setLoading(false))
  }, [])

  // Initial load: show everything.
  useEffect(() => { runSearch('', 'All Venice', []) }, [runSearch])

  const onToggleTag = (slug) => {
    const next = new Set(selectedTags)
    next.has(slug) ? next.delete(slug) : next.add(slug)
    setSelectedTags(next)
    // Tag changes auto-refresh only when there's no typed question (browsing
    // is free; a real search costs an LLM call, so that waits for submit).
    if (!query.trim()) runSearch('', neighborhood, Array.from(next))
  }

  const onNeighborhoodChange = (nb) => {
    setNeighborhood(nb)
    if (!query.trim()) runSearch('', nb, Array.from(selectedTags))
  }

  const onSearch = () => runSearch(query, neighborhood, Array.from(selectedTags))

  const recap = buildRecap(query.trim(), neighborhood, Array.from(selectedTags), tagLabelMap)

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 pb-20">
        <Header theme={theme} onToggleTheme={toggle} />
        <Hero />

        <div className="bg-card border border-line rounded-2xl p-5 md:p-6 mb-8">
          <SearchPanel
            query={query}
            onQueryChange={setQuery}
            neighborhood={neighborhood}
            onNeighborhoodChange={onNeighborhoodChange}
            onSearch={onSearch}
            neighborhoods={NEIGHBORHOODS}
          />
          <TagChips tags={tags} selected={selectedTags} onToggle={onToggleTag} />
        </div>

        <div className="text-[0.82rem] text-muted mb-4">
          ★ = average Google rating · the number in parentheses = how many reviews it's based on
        </div>

        <div className="text-[1.05rem] font-bold tracking-tight mb-1">{recap}</div>

        {loading && <CrostinoLoader />}
        {error && <div className="text-[0.9rem] text-coral-strong mb-4">Something went wrong: {error}</div>}
        {!loading && result?.status && <div className="text-[0.9rem] text-muted mb-4">{result.status}</div>}

        {result?.mode === 'search' && result.answer && !loading && (
          <AnswerBanner answer={result.answer} query={result.query} names={result.names} />
        )}

        <ResultsGrid
          loading={loading}
          isSearch={result?.mode === 'search'}
          items={result?.items || []}
          tagLabelMap={tagLabelMap}
          emptyText={
            result?.mode === 'search'
              ? 'No bars matched. Try a different question, neighborhood, or fewer tags.'
              : 'No bars match these filters yet. Try fewer tags or a different neighborhood.'
          }
        />
      </div>
    </div>
  )
}
