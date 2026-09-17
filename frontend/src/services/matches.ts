import { apiRequest } from '@/services/http'
export type MatchStatus = 'scheduled' | 'live' | 'completed' | 'cancelled'
export interface MatchRecord {
  id: number
  competition_id: number
  home_team_id: number
  away_team_id: number
  venue_id: number
  match_date: string
  start_time: string
  stage: string
  status: MatchStatus
  home_score: number | null
  away_score: number | null
  created_at: string
}
export type MatchInput = Omit<MatchRecord, 'id' | 'created_at'>
export const matchStatusLabels: Record<MatchStatus, string> = {
  scheduled: '未开始',
  live: '进行中',
  completed: '已结束',
  cancelled: '已取消',
}
export const listMatches = () => apiRequest<MatchRecord[]>('/api/matches')
export const getMatch = (id: number) => apiRequest<MatchRecord>(`/api/matches/${id}`)
export const createMatch = (input: MatchInput) =>
  apiRequest<MatchRecord>('/api/matches', { method: 'POST', body: JSON.stringify(input) })
export const updateMatch = (id: number, input: Partial<MatchInput>) =>
  apiRequest<MatchRecord>(`/api/matches/${id}`, { method: 'PATCH', body: JSON.stringify(input) })
export const deleteMatch = (id: number) =>
  apiRequest<void>(`/api/matches/${id}`, { method: 'DELETE' })
