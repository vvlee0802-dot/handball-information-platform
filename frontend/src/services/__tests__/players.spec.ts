import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPlayer, listPlayers, updatePlayer, type PlayerInput } from '@/services/players'

const input: PlayerInput = {
  name: '测试球员',
  number: 7,
  position: '中卫',
  team_id: 2,
  birth_date: '2000-01-01',
  description: null,
}

const mockResponse = (body: unknown, status = 200) => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('players service', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('filters players by team', async () => {
    const fetchMock = mockResponse([])
    await listPlayers(2)
    expect(fetchMock).toHaveBeenCalledWith('/api/players?team_id=2', expect.any(Object))
  })

  it('creates and updates players', async () => {
    let fetchMock = mockResponse({ id: 1, ...input, created_at: '2026-09-16T10:00:00Z' }, 201)
    await createPlayer(input)
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: 'POST' })

    fetchMock = mockResponse({
      id: 1,
      ...input,
      position: '左后卫',
      created_at: '2026-09-16T10:00:00Z',
    })
    await updatePlayer(1, { position: '左后卫' })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/players/1',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })
})
