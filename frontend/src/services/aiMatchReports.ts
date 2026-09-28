import { apiRequest } from './http'

export interface AiReportEvidence {
  id: string
  category: string
  label: string
  value: string
  event_id: number | null
  timestamp_seconds: number | null
}

export interface AiReportSection {
  heading: string
  body: string
  evidence_ids: string[]
}

export interface AiReportContent {
  title: string
  summary: string
  sections: AiReportSection[]
  limitations: string[]
}

export type AiReportFocus =
  | 'full_match'
  | 'key_phases'
  | 'team_comparison'
  | 'player_performance'
export type AiReportDetailLevel = 'concise' | 'detailed'

export interface AiReportEvaluationCheck {
  key: string
  label: string
  passed: boolean
  detail: string
  evidence_ids: string[]
}

export interface AiReportEvaluationRecord {
  id: string
  report_id: string
  match_id: number
  model_name: string
  prompt_version: string
  passed: boolean
  score: number
  checks: AiReportEvaluationCheck[]
  previous_evaluation_id: string | null
  previous_model_name: string | null
  previous_prompt_version: string | null
  previous_score: number | null
  score_delta: number | null
  created_at: string
}

export interface AiMatchReportRecord {
  id: string
  match_id: number
  status: string
  model_name: string
  prompt_version: string
  generation_focus: AiReportFocus
  detail_level: AiReportDetailLevel
  is_user_edited: boolean
  edited_at: string | null
  report: AiReportContent
  evidence: AiReportEvidence[]
  latest_evaluation: AiReportEvaluationRecord | null
  created_at: string
}

export const getLatestAiMatchReport = (matchId: number) =>
  apiRequest<AiMatchReportRecord | null>(`/api/matches/${matchId}/ai-reports/latest`)

export const listAiMatchReports = (matchId: number) =>
  apiRequest<AiMatchReportRecord[]>(`/api/matches/${matchId}/ai-reports`)

export const generateAiMatchReport = (
  matchId: number,
  options: { focus: AiReportFocus; detail_level: AiReportDetailLevel },
) =>
  apiRequest<AiMatchReportRecord>(`/api/matches/${matchId}/ai-reports`, {
    method: 'POST',
    body: JSON.stringify(options),
  })

export const updateAiMatchReport = (
  matchId: number,
  reportId: string,
  report: AiReportContent,
) =>
  apiRequest<AiMatchReportRecord>(`/api/matches/${matchId}/ai-reports/${reportId}`, {
    method: 'PATCH',
    body: JSON.stringify({ report }),
  })

export const evaluateAiMatchReport = (matchId: number, reportId: string) =>
  apiRequest<AiReportEvaluationRecord>(
    `/api/matches/${matchId}/ai-reports/${reportId}/evaluations`,
    { method: 'POST' },
  )
