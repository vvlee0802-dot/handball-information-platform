import { afterEach, describe, expect, it, vi } from 'vitest'
import { createTeam, updateTeam, type TeamInput } from '@/services/teams'
import { createVenue, updateVenue, type VenueInput } from '@/services/venues'

const mockJsonResponse = (body: unknown, status = 200) => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('team and venue services', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('creates and updates teams with the expected methods', async () => {
    const input: TeamInput = {
      name: '中国男子手球队',
      short_name: '中国',
      city: '北京',
      country: '中国',
      gender: 'men',
      description: null,
    }
    let fetchMock = mockJsonResponse({ id: 1, ...input, created_at: '2026-09-16T09:00:00Z' }, 201)
    await createTeam(input)
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: 'POST' })

    fetchMock = mockJsonResponse({
      id: 1,
      ...input,
      city: '上海',
      created_at: '2026-09-16T09:00:00Z',
    })
    await updateTeam(1, { city: '上海' })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/teams/1',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('creates and updates venues with the expected methods', async () => {
    const input: VenueInput = {
      name: '国家体育馆',
      city: '北京',
      address: '北京市朝阳区',
      capacity: 18000,
      description: null,
    }
    let fetchMock = mockJsonResponse({ id: 1, ...input, created_at: '2026-09-16T09:00:00Z' }, 201)
    await createVenue(input)
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: 'POST' })

    fetchMock = mockJsonResponse({
      id: 1,
      ...input,
      capacity: 20000,
      created_at: '2026-09-16T09:00:00Z',
    })
    await updateVenue(1, { capacity: 20000 })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/venues/1',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })
})
