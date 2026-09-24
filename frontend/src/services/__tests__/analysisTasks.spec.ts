import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  completedWithoutCandidates,
  getAnalysisTask,
  isLowConfidenceCandidate,
  listAnalysisPredictions,
  listMatchAnalysisTasks,
  reviewAnalysisPrediction,
  startVideoAnalysis,
  type AnalysisTaskRecord,
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

  it('loads prediction details and reviews a hard negative', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify([{ id: 9, outcome: 'false_positive' }]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: 9, outcome: 'false_positive', training_decision: 'include' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    vi.stubGlobal('fetch', fetchMock)

    await listAnalysisPredictions('task-123')
    await reviewAnalysisPrediction(9, 'include')

    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/analysis-tasks/task-123/predictions')
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/analysis-predictions/9/review')
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ decision: 'include' }),
      }),
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

  it('marks low-confidence candidates and explains empty completed results', () => {
    expect(isLowConfidenceCandidate(0.64)).toBe(true)
    expect(isLowConfidenceCandidate(0.65)).toBe(false)
    expect(isLowConfidenceCandidate(null)).toBe(false)

    const emptyCompletedTask = {
      status: 'completed',
      model_version: 'goal-detector-v2',
      candidate_count: 0,
    } as AnalysisTaskRecord
    expect(completedWithoutCandidates(emptyCompletedTask)).toBe(true)
    expect(completedWithoutCandidates({ ...emptyCompletedTask, candidate_count: 1 })).toBe(false)
  })
})
