import { apiRequest } from '@/services/http'

export interface OfficialReportPlayer {
  number: number
  name: string
  goals: number
  yellow_cards: number
  suspensions_2min: number
  red_cards: number
  blue_cards: number
}

export interface OfficialReportTeam {
  side: 'A' | 'B'
  code: string
  name: string
  half_time_score: number
  final_score: number
  seven_meter_goals: number
  seven_meter_attempts: number
  timeouts: string[]
  players: OfficialReportPlayer[]
}

export interface ParsedOfficialReport {
  report_type: string
  match_number: number | null
  competition_stage: string | null
  match_date: string | null
  start_time: string | null
  venue: string | null
  team_a: OfficialReportTeam
  team_b: OfficialReportTeam
}

export interface MatchReportPreview {
  id: string
  match_id: number
  original_filename: string
  status: 'pending' | 'imported'
  parsed: ParsedOfficialReport
  conflicts: string[]
  suggested_team_a_team_id: number | null
  suggested_team_b_team_id: number | null
  duplicate: boolean
  created_at: string
}

export interface OfficialPlayerStat {
  id: number
  team_id: number
  player_id: number | null
  player_name: string
  number: number
  goals: number
  yellow_cards: number
  suspensions_2min: number
  red_cards: number
  blue_cards: number
}

export interface OfficialTeamStat {
  id: number
  team_id: number
  report_side: 'A' | 'B'
  half_time_score: number
  final_score: number
  seven_meter_goals: number
  seven_meter_attempts: number
  timeouts: string[]
}

export interface MatchReportRecord {
  id: string
  match_id: number
  original_filename: string
  status: 'pending' | 'imported'
  parsed: ParsedOfficialReport
  conflicts: string[]
  team_a_team_id: number | null
  team_b_team_id: number | null
  player_stats: OfficialPlayerStat[]
  team_stats: OfficialTeamStat[]
  imported_at: string | null
  created_at: string
}

export const previewOfficialMatchReport = (matchId: number, file: File) =>
  apiRequest<MatchReportPreview>(`/api/matches/${matchId}/official-reports/preview`, {
    method: 'POST',
    body: file,
    headers: {
      'Content-Type': file.type || 'application/pdf',
      'X-Original-Filename': encodeURIComponent(file.name),
    },
  })

export const confirmOfficialMatchReport = (
  matchId: number,
  reportId: string,
  input: {
    team_a_team_id: number
    team_b_team_id: number
    accept_conflicts: boolean
  },
) =>
  apiRequest<MatchReportRecord>(
    `/api/matches/${matchId}/official-reports/${reportId}/confirm`,
    { method: 'POST', body: JSON.stringify(input) },
  )

export const getLatestOfficialMatchReport = (matchId: number) =>
  apiRequest<MatchReportRecord | null>(`/api/matches/${matchId}/official-reports/latest`)

