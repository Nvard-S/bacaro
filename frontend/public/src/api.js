// All calls go to the backend API. VITE_API_BASE_URL points at the deployed
// backend in production; empty means same-origin (handy for local dev proxy).
const BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function fetchTags() {
  const res = await fetch(`${BASE}/api/tags`)
  if (!res.ok) throw new Error('Could not load tags')
  const data = await res.json()
  return data.tags
}

export async function browse({ query, neighborhood, tags, topN = 9 }) {
  const res = await fetch(`${BASE}/api/browse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, neighborhood, tags, top_n: topN }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Search failed')
  return data
}
