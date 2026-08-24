import { useState } from 'react'
import { login, authConfigured } from '../lib/api.js'

export default function Login({ onLoggedIn }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!authConfigured()) {
      setError('Supabase is not configured (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY).')
      return
    }
    setBusy(true)
    try {
      await login(email.trim(), password)
      onLoggedIn()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-16 p-6 bg-white border border-gray-200 rounded-xl">
      <h1 className="text-xl font-bold mb-1">Bacaro Hop — Admin</h1>
      <p className="text-sm text-gray-500 mb-4">Sign in with your admin account.</p>
      <form onSubmit={submit}>
        <label className="block text-sm text-gray-600 mb-1">Email</label>
        <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-3 px-3 py-2 border border-gray-300 rounded" />
        <label className="block text-sm text-gray-600 mb-1">Password</label>
        <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-4 px-3 py-2 border border-gray-300 rounded" />
        <button type="submit" disabled={busy}
          className="px-4 py-2 rounded bg-blue-700 text-white font-semibold hover:bg-blue-800 disabled:opacity-60">
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        {error && <div className="text-red-600 text-sm mt-3">{error}</div>}
      </form>
    </div>
  )
}
