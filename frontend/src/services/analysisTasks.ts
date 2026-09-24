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
  model_version: string | null
  candidate_count: number
  evaluation_mode: boolean
  ground_truth_count: number
  true_positive_count: number
  false_positive_count: number
  false_negative_count: number
  precision: number | null
  recall: number | null
  f1: number | null
  mean_absolute_error_seconds: number | null
  failure_reason: string | null
  processing_started_at: string | null
  processing_completed_at: string | null
  created_at: string
  updated_at: string
  reused: boolean
}

export type AnalysisPredictionOutcome = 'true_positive' | 'false_positive' | 'false_negative'
export type TrainingDecision = 'pending' | 'include' | 'exclude'

export const AI_LOW_CONFIDENCE_THRESHOLD = 0.65

export interface AnalysisPredictionRecord {
  id: number
  analysis_task_id: string
  outcome: AnalysisPredictionOutcome
  predicted_timestamp_seconds: number | null
  confidence: number | null
  ground_truth_event_id: number | null
  ground_truth_timestamp_seconds: number | null
  time_error_seconds: number | null
  training_decision: TrainingDecision
  reviewed_by_user_id: number | null
  reviewed_at: string | null
  created_at: string
}

export const isLowConfidenceCandidate = (confidence: number | null) =>
  confidence !== null && confidence < AI_LOW_CONFIDENCE_THRESHOLD

export const completedWithoutCandidates = (task: AnalysisTaskRecord) =>
  task.status === 'completed' && task.model_version !== null && task.candidate_count === 0

export const listMatchAnalysisTasks = (matchId: number) =>
  apiRequest<AnalysisTaskRecord[]>(`/api/matches/${matchId}/analysis-tasks`)

export const startVideoAnalysis = (videoId: number) =>
  apiRequest<AnalysisTaskRecord>(`/api/videos/${videoId}/analysis-tasks`, {
    method: 'POST',
  })

export const getAnalysisTask = (taskId: string) =>
  apiRequest<AnalysisTaskRecord>(`/api/analysis-tasks/${taskId}`)

export const listAnalysisPredictions = (taskId: string) =>
  apiRequest<AnalysisPredictionRecord[]>(`/api/analysis-tasks/${taskId}/predictions`)

export const reviewAnalysisPrediction = (
  predictionId: number,
  decision: Exclude<TrainingDecision, 'pending'>,
) =>
  apiRequest<AnalysisPredictionRecord>(`/api/analysis-predictions/${predictionId}/review`, {
    method: 'POST',
    body: JSON.stringify({ decision }),
  })
