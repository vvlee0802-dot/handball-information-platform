import { apiRequest } from '@/services/http'

export interface PlayerRecord {
  id: number
  name: string
  number: number
  position: string
  team_id: number
  birth_date: string
  description: string | null
  created_at: string
}

export interface PlayerInput {
  name: string
  number: number
  position: string
  team_id: number
  birth_date: string
  description: string | null
}

export type PlayerUpdate = Partial<PlayerInput>

export const listPlayers = (teamId?: number) => {
  const query = teamId ? `?team_id=${teamId}` : ''
  return apiRequest<PlayerRecord[]>(`/api/players${query}`)
}

export const getPlayer = (playerId: number) => apiRequest<PlayerRecord>(`/api/players/${playerId}`)

export const createPlayer = (input: PlayerInput) =>
  apiRequest<PlayerRecord>('/api/players', {
    method: 'POST',
    body: JSON.stringify(input),
  })

export const updatePlayer = (playerId: number, input: PlayerUpdate) =>
  apiRequest<PlayerRecord>(`/api/players/${playerId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
