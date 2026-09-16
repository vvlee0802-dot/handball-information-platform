import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createCompetition,
  updateCompetition,
  type CompetitionInput,
} from '@/services/competitions'

describe('competitions service', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('creates a competition with a JSON POST request', async () => {
    const input: CompetitionInput = {
      name: '全国手球锦标赛',
      season: '2026',
      stage: '小组赛',
      status: 'active',
    }
    const created = {
      id: 1,
      ...input,
      created_at: '2026-09-16T06:30:00Z',
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(created), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(createCompetition(input)).resolves.toEqual(created)
    expect(fetchMock).toHaveBeenCalledWith('/api/competitions', {
      method: 'POST',
      body: JSON.stringify(input),
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    })
  })

  it('turns FastAPI validation details into a readable message', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [{ msg: 'String should have at least 1 character' }],
        }),
        {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      createCompetition({
        name: '',
        season: '2026',
        stage: null,
        status: 'draft',
      }),
    ).rejects.toThrow('String should have at least 1 character')
  })

  it('updates a competition with a JSON PATCH request', async () => {
    const update = {
      stage: '淘汰赛',
      status: 'active' as const,
    }
    const updated = {
      id: 7,
      name: '全国手球锦标赛',
      season: '2026',
      ...update,
      created_at: '2026-09-16T06:30:00Z',
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(updated), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(updateCompetition(7, update)).resolves.toEqual(updated)
    expect(fetchMock).toHaveBeenCalledWith('/api/competitions/7', {
      method: 'PATCH',
      body: JSON.stringify(update),
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    })
  })
})
