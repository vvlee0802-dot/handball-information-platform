import { apiRequest } from '@/services/http'

export type AnalysisTaskStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface AnalysisTaskRecord {
  id: string
  match_id: number
  video_id: number
  created_by_user_id: number
  task_type: 'goal_detection'
  status: AnalysisTaskStatus
  progress: number
  stage: string
  failure_reason: string | null
  processing_started_at: string | null
  processing_completed_at: string | null
  created_at: string
  updated_at: string
  reused: boolean
}

export const listMatchAnalysisTasks = (matchId: number) =>
  apiRequest<AnalysisTaskRecord[]>(`/api/matches/${matchId}/analysis-tasks`)

export const startVideoAnalysis = (videoId: number) =>
  apiRequest<AnalysisTaskRecord>(`/api/videos/${videoId}/analysis-tasks`, {
    method: 'POST',
  })

export const getAnalysisTask = (taskId: string) =>
  apiRequest<AnalysisTaskRecord>(`/api/analysis-tasks/${taskId}`)
