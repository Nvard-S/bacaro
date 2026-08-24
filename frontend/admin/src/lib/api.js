const BASE = import.meta.env.VITE_API_BASE_URL || ''
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || ''
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

// Use localStorage when it's actually usable (the browser), else fall back to
// an in-memory value -- keeps the app working in private-mode edge cases and
// non-browser contexts (like tests) instead of throwing.
let ls = null
try {
  ls = globalThis.localStorage
  if (ls) ls.getItem('__probe__')
} catch {
  ls = null
}
const mem = { token: '' }

export function getToken() { return (ls ? ls.getItem('admin_token') : mem.token) || '' }
export function setToken(t) { ls ? ls.setItem('admin_token', t) : (mem.token = t) }
export function clearToken() { ls ? ls.removeItem('admin_token') : (mem.token = '') }
export function authConfigured() { return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY) }

// Sign in against Supabase Auth directly; store the returned access token.
export async function login(email, password) {
  const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: SUPABASE_ANON_KEY },
    body: JSON.stringify({ email, password }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error_description || data.msg || 'Sign in failed')
  setToken(data.access_token)
}

// Authenticated fetch to the backend API. On 401 it clears the token and
// signals the app to drop back to the login screen.
export async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}), Authorization: `Bearer ${getToken()}` }
  const res = await fetch(`${BASE}${path}`, { ...opts, headers })
  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event('admin-logout'))
    throw new Error('Session expired — please sign in again.')
  }
  return res
}

export async function apiJson(path, opts) {
  const res = await api(path, opts)
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Request failed')
  return data
}
