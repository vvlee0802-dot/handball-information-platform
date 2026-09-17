import { apiRequest } from '@/services/http'

export type TeamGender = 'men' | 'women'

export interface TeamRecord {
  id: number
  name: string
  short_name: string
  city: string
  country: string
  gender: TeamGender
  description: string | null
  created_at: string
}

export interface TeamInput {
  name: string
  short_name: string
  city: string
  country: string
  gender: TeamGender
  description: string | null
}

export type TeamUpdate = Partial<TeamInput>

export const teamGenderLabels: Record<TeamGender, string> = {
  men: '男子',
  women: '女子',
}

export const listTeams = () => apiRequest<TeamRecord[]>('/api/teams')
export const getTeam = (teamId: number) => apiRequest<TeamRecord>(`/api/teams/${teamId}`)
export const createTeam = (input: TeamInput) =>
  apiRequest<TeamRecord>('/api/teams', {
    method: 'POST',
    body: JSON.stringify(input),
  })
export const updateTeam = (teamId: number, input: TeamUpdate) =>
  apiRequest<TeamRecord>(`/api/teams/${teamId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
export const deleteTeam = (teamId: number) =>
  apiRequest<void>(`/api/teams/${teamId}`, { method: 'DELETE' })
