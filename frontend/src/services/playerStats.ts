import { apiRequest } from '@/services/http'
import type { MatchEventRecord } from '@/services/events'

export type PlayerStatsMetric = 'goals' | 'shots' | 'saves' | 'turnovers' | 'fast_breaks'

export interface PlayerMatchStatsRecord {
  player_id: number
  player_name: string
  player_number: number
  position: string | null
  team_id: number
  team_name: string
  goals: number
  shots: number
  saves: number
  turnovers: number
  fast_breaks: number
  shooting_percentage: number | null
}

export interface MatchPlayerStatsRecord {
  match_id: number
  home_team_id: number
  home_team_name: string
  away_team_id: number
  away_team_name: string
  home_score: number | null
  away_score: number | null
  goal_source: 'official_report' | 'unavailable'
  official_report_id: string | null
  players: PlayerMatchStatsRecord[]
}

export const getMatchPlayerStats = (matchId: number) =>
  apiRequest<MatchPlayerStatsRecord>(`/api/matches/${matchId}/player-stats`)

export const getPlayerMetricEvents = (
  matchId: number,
  playerId: number,
  metric: PlayerStatsMetric,
) =>
  apiRequest<MatchEventRecord[]>(
    `/api/matches/${matchId}/player-stats/${playerId}/events?metric=${metric}`,
  )

export interface PlayerAssignmentBatchResult {
  requested_count: number
  affected_count: number
  events: MatchEventRecord[]
}

export const reassignEventPlayers = (matchId: number, eventIds: number[], playerId: number) =>
  apiRequest<PlayerAssignmentBatchResult>(
    `/api/matches/${matchId}/player-stats/player-assignment`,
    {
      method: 'POST',
      body: JSON.stringify({ event_ids: eventIds, player_id: playerId }),
    },
  )

export interface PlayerAssignmentAuditRecord {
  id: number
  match_id: number
  event_id: number
  old_player_id: number | null
  old_player_name: string | null
  new_player_id: number
  new_player_name: string
  changed_by_user_id: number
  changed_by_user_name: string
  changed_at: string
}

export const listPlayerAssignmentAudits = (matchId: number) =>
  apiRequest<PlayerAssignmentAuditRecord[]>(
    `/api/matches/${matchId}/player-stats/player-assignment/audits`,
  )
