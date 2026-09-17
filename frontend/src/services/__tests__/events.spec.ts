import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMatchEvent, listMatchEvents, type MatchEventInput } from '@/services/events'

describe('event services', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists a match timeline', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await listMatchEvents(12)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/events',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates a manual event at the selected timestamp', async () => {
    const input: MatchEventInput = {
      video_id: 8,
      event_type: 'goal',
      timestamp_seconds: 1112.4,
      team_id: 3,
      player_id: 28,
      note: '快攻进球',
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1, match_id: 12, ...input }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await createMatchEvent(12, input)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/events',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(input) }),
    )
  })
})
