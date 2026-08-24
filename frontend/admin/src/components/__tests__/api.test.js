import { describe, it, expect, beforeEach } from 'vitest'
import { getToken, setToken, clearToken } from '../../lib/api.js'

describe('token storage', () => {
  beforeEach(() => clearToken())

  it('starts empty', () => {
    expect(getToken()).toBe('')
  })

  it('stores and clears the admin token', () => {
    setToken('abc123')
    expect(getToken()).toBe('abc123')
    clearToken()
    expect(getToken()).toBe('')
  })
})
