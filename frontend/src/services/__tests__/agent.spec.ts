import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  confirmAgentProposal,
  createAgentSession,
  deleteAgentSession,
  getAgentSession,
  listAgentSessions,
  rejectAgentProposal,
  retryAgentRun,
  sendAgentMessage,
} from '@/services/agent'


const session = {
  id: 'session-1',
  user_id: 1,
  match_id: 1,
  match_label: '德国 vs 丹麦',
  title: '分析决赛',
  created_at: '2026-09-29T00:00:00Z',
  updated_at: '2026-09-29T00:00:00Z',
}

const detail = { session, messages: [], runs: [] }
const proposal = {
  id: 'proposal-1',
  run_id: 'run-1',
  session_id: session.id,
  match_id: 1,
  action_name: 'update_match_status',
  arguments: { status: 'cancelled' },
  summary: '修改比赛状态',
  status: 'pending',
  result: null,
  created_at: '2026-09-29T00:00:00Z',
  executed_at: null,
}

describe('agent service', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('manages sessions, messages, retries, and confirmed actions', async () => {
    const turn = {
      user_message: { id: 'm1', session_id: session.id, role: 'user', content: '谁赢了', sources: [], created_at: session.created_at },
      assistant_message: { id: 'm2', session_id: session.id, role: 'assistant', content: '丹麦获胜', sources: [], created_at: session.created_at },
      run: { id: 'run-1', session_id: session.id, status: 'completed', tool_calls: [], proposals: [] },
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([session]), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(detail), { status: 201, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(detail), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(turn), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(turn), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(proposal), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...proposal, status: 'rejected' }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await listAgentSessions()
    await createAgentSession(1)
    await getAgentSession(session.id)
    await sendAgentMessage(session.id, '谁赢了？')
    await retryAgentRun('run-1')
    await confirmAgentProposal(proposal.id)
    await rejectAgentProposal(proposal.id)
    await deleteAgentSession(session.id)

    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `/api/agent/sessions/${session.id}/messages`,
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ content: '谁赢了？' }) }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      `/api/agent/proposals/${proposal.id}/confirm`,
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
