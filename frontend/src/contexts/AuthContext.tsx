import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import type { UserOut, TokenResponse } from '@/types/auth'

interface AuthContextType {
  user: UserOut | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  isLoading: boolean
  error: string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'fiscalai_token'
const REFRESH_TOKEN_KEY = 'fiscalai_refresh'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [refreshToken, setRefreshToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Carrega tokens do localStorage ao montar e reidrata o usuário via GET /me
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)

    if (!storedToken) {
      setIsLoading(false)
      return
    }

    setToken(storedToken)
    setRefreshToken(storedRefreshToken)

    // Reidrata o usuário para que isAuthenticated seja true após reload
    fetch('/api/v1/auth/me', {
      headers: { 'Authorization': `Bearer ${storedToken}` },
    })
      .then(res => {
        if (!res.ok) throw new Error('token inválido')
        return res.json()
      })
      .then((userData: UserOut) => {
        setUser(userData)
      })
      .catch(() => {
        // Token expirado ou inválido — limpa tudo
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        setToken(null)
        setRefreshToken(null)
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    setError(null)

    try {
      // POST /auth/login
      const loginResponse = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (!loginResponse.ok) {
        const data = await loginResponse.json()
        throw new Error(data.detail || 'Login failed')
      }

      const tokenData: TokenResponse = await loginResponse.json()
      setToken(tokenData.access_token)
      setRefreshToken(tokenData.refresh_token)

      // Armazenar no localStorage
      localStorage.setItem(TOKEN_KEY, tokenData.access_token)
      localStorage.setItem(REFRESH_TOKEN_KEY, tokenData.refresh_token)

      // GET /auth/me para carregar dados do usuário
      const meResponse = await fetch('/api/v1/auth/me', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokenData.access_token}`,
        },
      })

      if (!meResponse.ok) {
        throw new Error('Failed to load user data')
      }

      const userData: UserOut = await meResponse.json()
      setUser(userData)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      // Limpar tudo em caso de erro
      setToken(null)
      setRefreshToken(null)
      setUser(null)
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_TOKEN_KEY)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    setIsLoading(true)

    try {
      // POST /auth/logout (best-effort - pode falhar se token expirou)
      if (token && refreshToken) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        }).catch(() => {
          // Melhor esforço — token já pode ter expirado
        })
      }
    } finally {
      // Sempre limpar estado local
      setToken(null)
      setRefreshToken(null)
      setUser(null)
      setError(null)
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_TOKEN_KEY)
      setIsLoading(false)
    }
  }

  const value: AuthContextType = {
    user,
    token,
    refreshToken,
    isAuthenticated: !!token && !!user,
    login,
    logout,
    isLoading,
    error,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth deve ser usado dentro de <AuthProvider>')
  }
  return context
}
