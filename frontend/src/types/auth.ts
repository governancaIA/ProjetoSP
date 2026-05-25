// Authentication types for JWT integration

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
}

export interface UserOut {
  id: number
  email: string
  full_name: string | null
  tenant_id: string
}

export interface AuthState {
  token: string | null
  refreshToken: string | null
  user: UserOut | null
  isAuthenticated: boolean
}
