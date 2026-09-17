import { apiRequest } from '@/services/http'

export type EventType =
  | 'goal'
  | 'shot'
  | 'save'
  | 'turnover'
  | 'foul'
  | 'suspension'
  | 'timeout'
  | 'seven_meter'
  | 'other'

export interface MatchEventRecord {
  id: number
  match_id: number
  video_id: number
  event_type: EventType
  timestamp_seconds: number
  team_id: number | null
  player_id: number | null
  note: string | null
  source: 'manual' | 'ai'
  status: 'draft' | 'verified'
  created_by_user_id: number
  updated_by_user_id: number
  verified_by_user_id: number | null
  verified_at: string | null
  created_at: string
  updated_at: string
}

export interface MatchEventInput {
  video_id: number
  event_type: EventType
  timestamp_seconds: number
  team_id: number | null
  player_id: number | null
  note: string | null
}

export const eventTypeLabels: Record<EventType, string> = {
  goal: '进球',
  shot: '射门',
  save: '扑救',
  turnover: '失误/球权转换',
  foul: '犯规',
  suspension: '两分钟处罚',
  timeout: '暂停',
  seven_meter: '七米球',
  other: '其他',
}

export const listMatchEvents = (matchId: number) =>
  apiRequest<MatchEventRecord[]>(`/api/matches/${matchId}/events`)

export const createMatchEvent = (matchId: number, input: MatchEventInput) =>
  apiRequest<MatchEventRecord>(`/api/matches/${matchId}/events`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
