import { apiRequest } from '@/services/http'
import type { EventType } from '@/services/events'

export type ClipExportStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface ClipExportSegmentRecord {
  event_id: number
  source_timestamp_seconds: number
  highlight_start_seconds: number
  duration_seconds: number
}

export interface ClipExportRecord {
  id: number
  match_id: number
  created_by_user_id: number
  event_ids: number[]
  status: ClipExportStatus
  filename: string
  export_type: 'event_clips' | 'player_highlight'
  player_id: number | null
  event_types: EventType[]
  segments: ClipExportSegmentRecord[]
  size_bytes: number | null
  duration_seconds: number | null
  failure_reason: string | null
  processing_started_at: string | null
  processing_completed_at: string | null
  created_at: string
}

export const listMatchClipExports = (matchId: number) =>
  apiRequest<ClipExportRecord[]>(`/api/matches/${matchId}/clip-exports`)

export const createClipExport = (matchId: number, eventIds: number[]) =>
  apiRequest<ClipExportRecord>(`/api/matches/${matchId}/clip-exports`, {
    method: 'POST',
    body: JSON.stringify({ event_ids: eventIds }),
  })

export const createPlayerHighlight = (
  matchId: number,
  playerId: number,
  eventTypes: EventType[],
) =>
  apiRequest<ClipExportRecord>(`/api/matches/${matchId}/player-highlights`, {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId, event_types: eventTypes }),
  })

export const deleteClipExport = (clipExportId: number) =>
  apiRequest<void>(`/api/clip-exports/${clipExportId}`, {
    method: 'DELETE',
  })

export const getClipExportContentUrl = (clipExportId: number, download = false) =>
  `/api/clip-exports/${clipExportId}/content${download ? '?download=true' : ''}`
