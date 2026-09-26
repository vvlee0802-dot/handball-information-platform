import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  createClipExport,
  createPlayerHighlight,
  deleteClipExport,
  getClipExportContentUrl,
  listMatchClipExports,
} from '@/services/clipExports'

describe('clip export services', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('creates and lists persistent export tasks', async () => {
    const responseBody = { id: 9, match_id: 12, event_ids: [2, 7], status: 'queued' }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await createClipExport(12, [2, 7])

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/clip-exports',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ event_ids: [2, 7] }) }),
    )

    fetchMock.mockResolvedValueOnce(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    await listMatchClipExports(12)
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/matches/12/clip-exports',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('builds preview and download URLs', () => {
    expect(getClipExportContentUrl(9)).toBe('/api/clip-exports/9/content')
    expect(getClipExportContentUrl(9, true)).toBe(
      '/api/clip-exports/9/content?download=true',
    )
  })

  it('creates a player highlight for selected event types', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 7, status: 'queued' }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await createPlayerHighlight(12, 8, ['goal', 'save'])

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/matches/12/player-highlights',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ player_id: 8, event_types: ['goal', 'save'] }),
      }),
    )
  })

  it('deletes a generated export task', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await deleteClipExport(9)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/clip-exports/9',
      expect.objectContaining({ method: 'DELETE', credentials: 'include' }),
    )
  })
})
