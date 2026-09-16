import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMatch, updateMatch, type MatchInput } from '@/services/matches'

const input: MatchInput = {
  competition_id: 1,
  home_team_id: 1,
  away_team_id: 2,
  venue_id: 1,
  match_date: '2026-10-01',
  start_time: '19:30:00',
  stage: '小组赛',
  status: 'scheduled',
  home_score: null,
  away_score: null,
}
const respond = (body: unknown, status = 200) => {
  const mock = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  vi.stubGlobal('fetch', mock)
  return mock
}

describe('matches service', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('creates and updates a match', async () => {
    let mock = respond({ id: 1, ...input, created_at: '2026-09-16T10:00:00Z' }, 201)
    await createMatch(input)
    expect(mock.mock.calls[0]?.[1]).toMatchObject({ method: 'POST' })
    mock = respond({
      id: 1,
      ...input,
      status: 'completed',
      home_score: 30,
      away_score: 28,
      created_at: '2026-09-16T10:00:00Z',
    })
    await updateMatch(1, { status: 'completed', home_score: 30, away_score: 28 })
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/1',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })
})
