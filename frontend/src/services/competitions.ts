import { apiRequest } from '@/services/http'

export type CompetitionStatus = 'draft' | 'active' | 'completed' | 'archived'

export interface CompetitionRecord {
  id: number
  name: string
  season: string
  stage: string | null
  status: CompetitionStatus
  created_at: string
}

export interface CompetitionInput {
  name: string
  season: string
  stage: string | null
  status: CompetitionStatus
}

export type CompetitionUpdate = Partial<CompetitionInput>

export const competitionStatusLabels: Record<CompetitionStatus, string> = {
  draft: '草稿',
  active: '进行中',
  completed: '已结束',
  archived: '已归档',
}

export const listCompetitions = () => apiRequest<CompetitionRecord[]>('/api/competitions')

export const getCompetition = (competitionId: number) =>
  apiRequest<CompetitionRecord>(`/api/competitions/${competitionId}`)

export const createCompetition = (input: CompetitionInput) =>
  apiRequest<CompetitionRecord>('/api/competitions', {
    method: 'POST',
    body: JSON.stringify(input),
  })

export const updateCompetition = (competitionId: number, input: CompetitionUpdate) =>
  apiRequest<CompetitionRecord>(`/api/competitions/${competitionId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
