import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createMatchEvent,
  deleteMatchEvent,
  listMatchEvents,
  updateMatchEvent,
  validateEventTimestamp,
  verifyMatchEvent,
  type MatchEventInput,
} from '@/services/events'

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

  it('serializes timeline filters and rejects invalid jump timestamps', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await listMatchEvents(12, {
      event_type: 'goal',
      team_id: 3,
      player_id: 28,
      status: 'verified',
    })

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      '/api/matches/12/events?event_type=goal&team_id=3&player_id=28&status=verified',
    )
    expect(validateEventTimestamp(30, 90)).toBeNull()
    expect(validateEventTimestamp(-1, 90)).toBe('事件时间戳无效。')
    expect(validateEventTimestamp(91, 90)).toBe('事件时间超过视频时长，无法跳转。')
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

  it('updates, verifies and deletes an event with the expected endpoints', async () => {
    let fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 5, status: 'draft' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await updateMatchEvent(12, 5, { event_type: 'goal', timestamp_seconds: 44.5 })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/events/5',
      expect.objectContaining({ method: 'PATCH' }),
    )

    fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 5, status: 'verified' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await verifyMatchEvent(12, 5)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/events/5/verify',
      expect.objectContaining({ method: 'POST' }),
    )

    fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
    await deleteMatchEvent(12, 5)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/events/5',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})
