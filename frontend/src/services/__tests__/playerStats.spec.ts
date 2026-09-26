import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  getMatchPlayerStats,
  getPlayerMetricEvents,
  listPlayerAssignmentAudits,
  reassignEventPlayers,
} from '@/services/playerStats'

describe('player stats service', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('loads verified player statistics for a match', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ match_id: 12, players: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await getMatchPlayerStats(12)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/player-stats',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('loads metric events and updates player assignments', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await getPlayerMetricEvents(12, 8, 'shots')
    await reassignEventPlayers(12, [2, 3], 9)
    await listPlayerAssignmentAudits(12)

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      '/api/matches/12/player-stats/8/events?metric=shots',
    )
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      '/api/matches/12/player-stats/player-assignment',
    )
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ event_ids: [2, 3], player_id: 9 }),
      }),
    )
    expect(fetchMock.mock.calls[2]?.[0]).toBe(
      '/api/matches/12/player-stats/player-assignment/audits',
    )
  })
})
