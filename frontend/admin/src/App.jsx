import { useEffect, useState } from 'react'
import Login from './components/Login.jsx'
import AdminPanel from './components/AdminPanel.jsx'
import { getToken, clearToken } from './lib/api.js'

export default function App() {
  const [token, setTok] = useState(getToken())

  useEffect(() => {
    const onLogout = () => setTok('')
    window.addEventListener('admin-logout', onLogout)
    return () => window.removeEventListener('admin-logout', onLogout)
  }, [])

  if (!token) return <Login onLoggedIn={() => setTok(getToken())} />
  return <AdminPanel onLogout={() => { clearToken(); setTok('') }} />
}
