import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const TOKEN_KEY = 'theme_trader_token'
const USER_KEY = 'theme_trader_user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })

  const loginWithToken = useCallback((accessToken, userObj) => {
    setToken(accessToken)
    setUser(userObj)
    localStorage.setItem(TOKEN_KEY, accessToken)
    if (userObj) localStorage.setItem(USER_KEY, JSON.stringify(userObj))
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }, [])

  const value = useMemo(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      loginWithToken,
      logout,
      authHeader: token ? { Authorization: `Bearer ${token}` } : {},
    }),
    [token, user, loginWithToken, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
