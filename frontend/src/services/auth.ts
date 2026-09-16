import { apiRequest } from './http'

export interface AuthUser {
  id: number
  email: string
  display_name: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export const login = (credentials: LoginCredentials) =>
  apiRequest<AuthUser>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
    redirectOnUnauthorized: false,
  })

export const getCurrentUser = () =>
  apiRequest<AuthUser>('/api/auth/me', {
    redirectOnUnauthorized: false,
  })

export const logout = () =>
  apiRequest<void>('/api/auth/logout', {
    method: 'POST',
    redirectOnUnauthorized: false,
  })
