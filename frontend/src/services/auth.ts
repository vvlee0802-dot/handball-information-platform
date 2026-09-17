import { apiRequest } from './http'

export type UserRole = 'athlete' | 'coach_analyst' | 'competition_admin' | 'system_admin'

export type Permission =
  | 'view_authorized_video'
  | 'upload_and_annotate_video'
  | 'manage_competition_data'
  | 'generate_reports'
  | 'manage_users'

export interface AuthUser {
  id: number
  email: string
  display_name: string
  role: UserRole
  is_active: boolean
  permissions: Permission[]
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
