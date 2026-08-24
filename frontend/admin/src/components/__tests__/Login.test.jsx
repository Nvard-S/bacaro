import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Login from '../Login.jsx'

describe('Login', () => {
  it('renders a sign-in button', () => {
    render(<Login onLoggedIn={() => {}} />)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('warns when Supabase env vars are missing', async () => {
    // In the test env VITE_SUPABASE_URL / ANON_KEY are unset, so authConfigured() is false.
    render(<Login onLoggedIn={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByText(/not configured/i)).toBeInTheDocument()
  })
})
