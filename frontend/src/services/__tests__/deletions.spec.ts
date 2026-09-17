import { afterEach, describe, expect, it, vi } from 'vitest'

import { deleteCompetition } from '@/services/competitions'
import { deleteMatch } from '@/services/matches'
import { deletePlayer } from '@/services/players'
import { deleteTeam } from '@/services/teams'
import { deleteVenue } from '@/services/venues'


describe('base entity deletion services', () => {
  afterEach(() => vi.unstubAllGlobals())

  it.each([
    ['competition', deleteCompetition, '/api/competitions/7'],
    ['match', deleteMatch, '/api/matches/7'],
    ['team', deleteTeam, '/api/teams/7'],
    ['player', deletePlayer, '/api/players/7'],
    ['venue', deleteVenue, '/api/venues/7'],
  ])('deletes a %s with an authenticated DELETE request', async (_name, remove, path) => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(remove(7)).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith(
      path,
      expect.objectContaining({ method: 'DELETE', credentials: 'include' }),
    )
  })
})
