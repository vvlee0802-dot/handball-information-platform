import { apiRequest } from '@/services/http'

export interface AgentSession {
  id: string
  user_id: number
  match_id: number | null
  match_label: string | null
  title: string
  created_at: string
  updated_at: string
}

export interface AgentSource {
  id: string
  source_type: 'match' | 'event' | 'player_stat' | 'knowledge'
  label: string
  match_id: number | null
  event_id: number | null
  player_id: number | null
  document_id: string | null
  timestamp_seconds: number | null
  excerpt: string | null
}

export interface AgentMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  sources: AgentSource[]
  created_at: string
}

export interface AgentToolCall {
  id: string
  run_id: string
  sequence: number
  tool_name: string
  status: 'running' | 'completed' | 'failed' | 'denied'
  duration_ms: number
  arguments_summary: Record<string, unknown>
  result_summary: Record<string, unknown> | null
  retryable: boolean
  error_message: string | null
  created_at: string
}

export interface AgentActionProposal {
  id: string
  run_id: string
  session_id: string
  match_id: number | null
  action_name: string
  arguments: Record<string, unknown>
  summary: string
  status: 'pending' | 'executed' | 'rejected' | 'failed'
  result: Record<string, unknown> | null
  created_at: string
  executed_at: string | null
}

export interface AgentRun {
  id: string
  session_id: string
  user_message_id: string | null
  assistant_message_id: string | null
  retry_of_run_id: string | null
  status: 'running' | 'completed' | 'failed'
  model_name: string
  prompt_version: string
  latency_ms: number | null
  token_usage: Record<string, number>
  error_type: string | null
  error_message: string | null
  tool_calls: AgentToolCall[]
  proposals: AgentActionProposal[]
  created_at: string
  completed_at: string | null
}

export interface AgentSessionDetail {
  session: AgentSession
  messages: AgentMessage[]
  runs: AgentRun[]
}

export interface AgentTurn {
  user_message: AgentMessage
  assistant_message: AgentMessage | null
  run: AgentRun
}

export const listAgentSessions = () =>
  apiRequest<AgentSession[]>('/api/agent/sessions')

export const createAgentSession = (matchId: number | null) =>
  apiRequest<AgentSessionDetail>('/api/agent/sessions', {
    method: 'POST',
    body: JSON.stringify({ match_id: matchId }),
  })

export const getAgentSession = (sessionId: string) =>
  apiRequest<AgentSessionDetail>(`/api/agent/sessions/${sessionId}`)

export const deleteAgentSession = (sessionId: string) =>
  apiRequest<void>(`/api/agent/sessions/${sessionId}`, { method: 'DELETE' })

export const sendAgentMessage = (sessionId: string, content: string) =>
  apiRequest<AgentTurn>(`/api/agent/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })

export const retryAgentRun = (runId: string) =>
  apiRequest<AgentTurn>(`/api/agent/runs/${runId}/retry`, { method: 'POST' })

export const confirmAgentProposal = (proposalId: string) =>
  apiRequest<AgentActionProposal>(`/api/agent/proposals/${proposalId}/confirm`, {
    method: 'POST',
  })

export const rejectAgentProposal = (proposalId: string) =>
  apiRequest<AgentActionProposal>(`/api/agent/proposals/${proposalId}/reject`, {
    method: 'POST',
  })
