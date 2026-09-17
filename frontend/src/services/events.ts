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

export type MatchEventUpdate = Partial<Omit<MatchEventInput, 'video_id'>>

export interface MatchEventFilters {
  event_type?: EventType
  team_id?: number
  player_id?: number
  status?: 'draft' | 'verified'
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

export const listMatchEvents = (matchId: number, filters: MatchEventFilters = {}) => {
  const query = new URLSearchParams()
  if (filters.event_type) query.set('event_type', filters.event_type)
  if (filters.team_id) query.set('team_id', String(filters.team_id))
  if (filters.player_id) query.set('player_id', String(filters.player_id))
  if (filters.status) query.set('status', filters.status)
  const suffix = query.size > 0 ? `?${query.toString()}` : ''
  return apiRequest<MatchEventRecord[]>(`/api/matches/${matchId}/events${suffix}`)
}

export const validateEventTimestamp = (
  timestampSeconds: number,
  durationSeconds: number | null,
): string | null => {
  if (!Number.isFinite(timestampSeconds) || timestampSeconds < 0) return '事件时间戳无效。'
  if (durationSeconds !== null && timestampSeconds > durationSeconds) {
    return '事件时间超过视频时长，无法跳转。'
  }
  return null
}

export const createMatchEvent = (matchId: number, input: MatchEventInput) =>
  apiRequest<MatchEventRecord>(`/api/matches/${matchId}/events`, {
    method: 'POST',
    body: JSON.stringify(input),
  })

export const updateMatchEvent = (
  matchId: number,
  eventId: number,
  input: MatchEventUpdate,
) =>
  apiRequest<MatchEventRecord>(`/api/matches/${matchId}/events/${eventId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })

export const deleteMatchEvent = (matchId: number, eventId: number) =>
  apiRequest<void>(`/api/matches/${matchId}/events/${eventId}`, { method: 'DELETE' })

export const verifyMatchEvent = (matchId: number, eventId: number) =>
  apiRequest<MatchEventRecord>(`/api/matches/${matchId}/events/${eventId}/verify`, {
    method: 'POST',
  })
