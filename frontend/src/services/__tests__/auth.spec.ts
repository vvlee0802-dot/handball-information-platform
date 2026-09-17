import { afterEach, describe, expect, it, vi } from 'vitest'

import { getCurrentUser, login, logout } from '@/services/auth'
import { apiRequest } from '@/services/http'


const user = {
  id: 1,
  email: 'coach@example.com',
  display_name: '王教练',
  role: 'coach_analyst',
  is_active: true,
  permissions: ['view_authorized_video', 'upload_and_annotate_video', 'generate_reports'],
}

describe('authentication service', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('logs in with JSON credentials and includes cookies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(user), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      login({ email: 'coach@example.com', password: 'correct-password' }),
    ).resolves.toEqual(user)
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: 'coach@example.com',
        password: 'correct-password',
      }),
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    })
  })

  it('handles a successful logout with an empty response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))

    await expect(logout()).resolves.toBeUndefined()
  })

  it('does not redirect when the initial session check is unauthorized', async () => {
    const unauthorizedHandler = vi.fn()
    window.addEventListener('auth:unauthorized', unauthorizedHandler)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Authentication required' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(getCurrentUser()).rejects.toThrow('Authentication required')
    expect(unauthorizedHandler).not.toHaveBeenCalled()
    window.removeEventListener('auth:unauthorized', unauthorizedHandler)
  })

  it('announces an expired session for protected requests', async () => {
    const unauthorizedHandler = vi.fn()
    window.addEventListener('auth:unauthorized', unauthorizedHandler)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Session expired or invalid' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(apiRequest('/api/protected')).rejects.toThrow('Session expired or invalid')
    expect(unauthorizedHandler).toHaveBeenCalledOnce()
    window.removeEventListener('auth:unauthorized', unauthorizedHandler)
  })
})
