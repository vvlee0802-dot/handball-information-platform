import { apiRequest } from '@/services/http'

export type ClipExportStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface ClipExportRecord {
  id: number
  match_id: number
  created_by_user_id: number
  event_ids: number[]
  status: ClipExportStatus
  filename: string
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

export const getClipExportContentUrl = (clipExportId: number, download = false) =>
  `/api/clip-exports/${clipExportId}/content${download ? '?download=true' : ''}`
