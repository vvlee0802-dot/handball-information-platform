import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  evaluateAiMatchReport,
  generateAiMatchReport,
  getLatestAiMatchReport,
  listAiMatchReports,
  updateAiMatchReport,
} from '@/services/aiMatchReports'

const respond = (body: unknown, status = 200) => {
  const mock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', mock)
  return mock
}

describe('AI match report service', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('loads and generates match reports from the match-scoped API', async () => {
    let mock = respond(null)
    await getLatestAiMatchReport(38)
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/ai-reports/latest',
      expect.objectContaining({ credentials: 'include' }),
    )

    mock = respond({ id: 'ai-report-1' }, 201)
    await generateAiMatchReport(38, { focus: 'team_comparison', detail_level: 'detailed' })
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/ai-reports',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ focus: 'team_comparison', detail_level: 'detailed' }),
      }),
    )
  })

  it('lists, edits and evaluates saved report versions', async () => {
    let mock = respond([])
    await listAiMatchReports(38)
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/ai-reports',
      expect.objectContaining({ credentials: 'include' }),
    )

    const report = { title: '标题', summary: '摘要', sections: [], limitations: [] }
    mock = respond({ id: 'report-1' })
    await updateAiMatchReport(38, 'report-1', report)
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/ai-reports/report-1',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ report }) }),
    )

    mock = respond({ id: 'evaluation-1' }, 201)
    await evaluateAiMatchReport(38, 'report-1')
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/ai-reports/report-1/evaluations',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
