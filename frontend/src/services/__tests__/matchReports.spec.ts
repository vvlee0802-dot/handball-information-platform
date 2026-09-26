import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  confirmOfficialMatchReport,
  getLatestOfficialMatchReport,
  previewOfficialMatchReport,
} from '@/services/matchReports'

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

describe('official match report service', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uploads a PDF as the raw request body', async () => {
    const mock = respond({ id: 'report-1', status: 'pending' })
    const file = new File(['%PDF-test'], '赛后统计.pdf', { type: 'application/pdf' })
    await previewOfficialMatchReport(38, file)
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/official-reports/preview',
      expect.objectContaining({
        method: 'POST',
        body: file,
        credentials: 'include',
        headers: expect.objectContaining({
          'Content-Type': 'application/pdf',
          'X-Original-Filename': encodeURIComponent(file.name),
        }),
      }),
    )
  })

  it('confirms mappings and loads the latest imported report', async () => {
    let mock = respond({ id: 'report-1', status: 'imported' })
    await confirmOfficialMatchReport(38, 'report-1', {
      team_a_team_id: 1,
      team_b_team_id: 2,
      accept_conflicts: true,
    })
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/official-reports/report-1/confirm',
      expect.objectContaining({ method: 'POST' }),
    )

    mock = respond(null)
    await getLatestOfficialMatchReport(38)
    expect(mock).toHaveBeenCalledWith(
      '/api/matches/38/official-reports/latest',
      expect.objectContaining({ credentials: 'include' }),
    )
  })
})

