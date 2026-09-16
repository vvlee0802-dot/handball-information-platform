import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  type AuthUser,
  type LoginCredentials,
} from '@/services/auth'
import { ApiError } from '@/services/http'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const initialized = ref(false)
  const isAuthenticated = computed(() => user.value !== null)

  const restoreSession = async () => {
    try {
      user.value = await getCurrentUser()
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error
      user.value = null
    } finally {
      initialized.value = true
    }
  }

  const login = async (credentials: LoginCredentials) => {
    user.value = await loginRequest(credentials)
    initialized.value = true
  }

  const logout = async () => {
    try {
      await logoutRequest()
    } finally {
      user.value = null
      initialized.value = true
    }
  }

  const clearSession = () => {
    user.value = null
    initialized.value = true
  }

  return {
    user,
    initialized,
    isAuthenticated,
    restoreSession,
    login,
    logout,
    clearSession,
  }
})
