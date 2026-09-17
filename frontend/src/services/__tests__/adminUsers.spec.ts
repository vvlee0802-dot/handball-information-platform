import { afterEach, describe, expect, it, vi } from 'vitest'

import { createAdminUser, listAdminUsers, updateAdminUser } from '@/services/adminUsers'


describe('admin user service', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists, creates, and updates users through the protected admin API', async () => {
    const user = {
      id: 2,
      email: 'coach@example.com',
      display_name: '王教练',
      role: 'coach_analyst',
      is_active: true,
      permissions: ['view_authorized_video'],
      extra_permissions: [],
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify([user]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(user), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...user, is_active: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    await expect(listAdminUsers()).resolves.toEqual([user])
    await createAdminUser({
      email: user.email,
      display_name: user.display_name,
      password: 'initial-password',
      role: 'coach_analyst',
      extra_permissions: [],
    })
    await updateAdminUser(user.id, { is_active: false })

    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/admin/users/2',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ is_active: false }) }),
    )
  })
})
