import { useState } from 'react'
import SettingsStatus from './SettingsStatus.jsx'
import CollectSection from './CollectSection.jsx'
import BackgroundJobSection from './BackgroundJobSection.jsx'
import IndexSection from './IndexSection.jsx'
import SearchSection from './SearchSection.jsx'
import SummarySection from './SummarySection.jsx'

const NEIGHBORHOODS = ['Cannaregio', 'Castello', 'San Marco', 'Dorsoduro', 'San Polo', 'Santa Croce', 'All Venice']
const SEARCH_NB = ['All Venice', 'Cannaregio', 'Castello', 'San Marco', 'Dorsoduro', 'San Polo', 'Santa Croce']

function enrichProgress(p) {
  if (!p.total) return `Nothing to process (${p.skipped || 0} already have content, or no website).`
  const parts = [`${p.done || 0} / ${p.total} done`]
  if (p.errors) parts.push(`${p.errors} errors`)
  parts.push(`${p.skipped || 0} skipped`)
  return parts.join(', ') + (p.running ? '…' : ' — done.')
}
function tagProgress(p) {
  if (!p.total) return 'Nothing to tag — every bar already has tags.'
  const parts = [`${p.done || 0} / ${p.total} done`]
  if (p.errors) parts.push(`${p.errors} errors`)
  return parts.join(', ') + (p.running ? '…' : ' — done.')
}
function instaProgress(p) {
  if (!p.total) return 'Nothing to do — every bar with a website has been checked.'
  const parts = [`${p.done || 0} / ${p.total} done`, `${p.found_direct || 0} direct`, `${p.found_parallel || 0} via Parallel`]
  if (p.errors) parts.push(`${p.errors} errors`)
  return parts.join(', ') + (p.running ? '…' : ' — done.')
}

export default function AdminPanel({ onLogout }) {
  const [neighborhood, setNeighborhood] = useState('Cannaregio')
  const [refreshKey, setRefreshKey] = useState(0)
  const bumpSummary = () => setRefreshKey((k) => k + 1)

  return (
    <div className="max-w-2xl mx-auto px-5 py-8">
      <div className="flex justify-between items-baseline mb-4">
        <h1 className="text-2xl font-bold">Bacaro Hop — Admin</h1>
        <button onClick={onLogout} className="text-sm text-blue-700 hover:underline">Sign out</button>
      </div>

      <SettingsStatus />
      <CollectSection
        neighborhood={neighborhood}
        setNeighborhood={setNeighborhood}
        neighborhoods={NEIGHBORHOODS}
        onCollected={bumpSummary}
      />
      <BackgroundJobSection
        n={3} title="Enrich with cicchetti content"
        note="For each bar with a website and no content yet, extracts cicchetti details from the site (Parallel)."
        buttonLabel="Fetch cicchetti content"
        startPath="/api/fetch-cicchetti-content"
        progressPath="/api/fetch-cicchetti-content/progress"
        getBody={() => ({ neighborhood })}
        renderProgress={enrichProgress}
      />
      <BackgroundJobSection
        n={4} title="Tag bars"
        note="Classifies each untagged bar against the fixed tag list (OpenAI). Powers the public filters."
        buttonLabel="Tag bars"
        startPath="/api/tag-bars"
        progressPath="/api/tag-bars/progress"
        renderProgress={tagProgress}
      />
      <BackgroundJobSection
        n={5} title="Find Instagram links"
        note="For bars with a website but no Instagram yet: direct scan first, then Parallel fallback. Best-effort."
        buttonLabel="Find Instagram links"
        startPath="/api/find-instagram"
        progressPath="/api/find-instagram/progress"
        renderProgress={instaProgress}
      />
      <IndexSection />
      <SearchSection neighborhoods={SEARCH_NB} />
      <SummarySection neighborhood={neighborhood} refreshKey={refreshKey} />
    </div>
  )
}
