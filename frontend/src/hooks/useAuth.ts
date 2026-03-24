import { useState, useEffect, useCallback } from 'react'
import { login as apiLogin, signup as apiSignup, fetchMe } from '@/lib/api'
import type { User } from '@/types'

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    const storedUser = localStorage.getItem(USER_KEY)
    if (storedToken && storedUser) {
      setToken(storedToken)
      try {
        setUser(JSON.parse(storedUser))
      } catch {
        setUser(null)
      }
    }
    setLoading(false)
  }, [])

  const persist = (nextUser: User, nextToken: string) => {
    setUser(nextUser)
    setToken(nextToken)
    localStorage.setItem(TOKEN_KEY, nextToken)
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
  }

  const clear = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const login = useCallback(async (email: string, password: string) => {
    setError(null)
    try {
      const res = await apiLogin(email, password)
      persist(res.user, res.token)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed'
      setError(message)
      throw err
    }
  }, [])

  const signup = useCallback(async (email: string, password: string, name?: string) => {
    setError(null)
    try {
      const res = await apiSignup(email, password, name)
      persist(res.user, res.token)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Signup failed'
      setError(message)
      throw err
    }
  }, [])

  const refresh = useCallback(async () => {
    if (!token) return
    try {
      const me = await fetchMe(token)
      persist(me, token)
    } catch (err) {
      console.error('Auth refresh failed', err)
      clear()
    }
  }, [token])

  const logout = () => clear()

  return { user, token, loading, error, login, signup, logout, refresh }
}