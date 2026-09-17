import { apiRequest } from './http'
import type { Permission, UserRole } from './auth'

export interface AdminUser {
  id: number
  email: string
  display_name: string
  role: UserRole
  is_active: boolean
  permissions: Permission[]
  extra_permissions: Permission[]
}

export interface AdminUserCreate {
  email: string
  display_name: string
  password: string
  role: UserRole
  extra_permissions: Permission[]
}

export interface AdminUserUpdate {
  display_name?: string
  role?: UserRole
  is_active?: boolean
  extra_permissions?: Permission[]
}

export const listAdminUsers = () => apiRequest<AdminUser[]>('/api/admin/users')

export const createAdminUser = (data: AdminUserCreate) =>
  apiRequest<AdminUser>('/api/admin/users', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateAdminUser = (userId: number, data: AdminUserUpdate) =>
  apiRequest<AdminUser>(`/api/admin/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
