import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  getAnalysisTask,
  listMatchAnalysisTasks,
  startVideoAnalysis,
} from '@/services/analysisTasks'

describe('analysis task services', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('starts an AI analysis task and immediately receives its ID', async () => {
    const responseBody = {
      id: 'task-123',
      video_id: 8,
      status: 'queued',
      progress: 0,
      reused: false,
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(startVideoAnalysis(8)).resolves.toEqual(responseBody)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/videos/8/analysis-tasks',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })

  it('restores task state from match and task endpoints', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await listMatchAnalysisTasks(12)
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/matches/12/analysis-tasks')

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: 'task-123', status: 'running' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await getAnalysisTask('task-123')
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/analysis-tasks/task-123')
  })
})
