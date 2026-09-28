import { apiRequest } from '@/services/http'

export type KnowledgeVisibility = 'platform' | 'team_private' | 'owner_private'
export type KnowledgeDocumentStatus = 'processing' | 'ready' | 'failed'

export interface DocumentChunkRecord {
  id: number
  ordinal: number
  content: string
  page_number: number | null
  section_title: string | null
}

export interface KnowledgeDocumentRecord {
  id: string
  owner_user_id: number
  owner_name: string
  team_id: number | null
  team_name: string | null
  original_filename: string
  content_type: string
  size_bytes: number
  visibility: KnowledgeVisibility
  status: KnowledgeDocumentStatus
  parser_name: string
  page_count: number
  chunk_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeDocumentDetail extends KnowledgeDocumentRecord {
  chunks: DocumentChunkRecord[]
}

export interface KnowledgeCitation {
  chunk_id: number
  document_id: string
  document_name: string
  page_number: number | null
  section_title: string | null
  excerpt: string
  score: number
}

export interface KnowledgeAnswer {
  answer: string
  citations: KnowledgeCitation[]
  insufficient_evidence: boolean
  answer_model: string
  embedding_model: string
  prompt_version: string
}

export interface RagEvaluationCase {
  id: number
  question: string
  expected_document_ids: string[]
  owner_user_id: number
  team_id: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RagRetrievedChunk {
  chunk_id: number
  document_id: string
  page_number: number | null
  section_title: string | null
  score: number
}

export interface RagEvaluationDetail {
  case_id: number
  question: string
  expected_document_ids: string[]
  retrieved_chunks: RagRetrievedChunk[]
  answer: string
  insufficient_evidence: boolean
  citation_chunk_ids: number[]
  citation_document_ids: string[]
  recall_at_k: number
  citation_hit_rate: number
  ungrounded: boolean
}

export interface RagEvaluationRun {
  id: string
  run_by_user_id: number
  team_id: number | null
  embedding_model: string
  answer_model: string
  prompt_version: string
  top_k: number
  relevance_threshold: number
  case_count: number
  recall_at_k: number
  citation_hit_rate: number
  ungrounded_answer_rate: number
  details: RagEvaluationDetail[]
  created_at: string
}

export const listKnowledgeDocuments = () =>
  apiRequest<KnowledgeDocumentRecord[]>('/api/knowledge/documents')

export const getKnowledgeDocument = (documentId: string) =>
  apiRequest<KnowledgeDocumentDetail>(`/api/knowledge/documents/${documentId}`)

export const uploadKnowledgeDocument = (
  file: File,
  visibility: KnowledgeVisibility,
  teamId: number | null = null,
) =>
  apiRequest<KnowledgeDocumentDetail>('/api/knowledge/documents', {
    method: 'POST',
    body: file,
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
      'X-Original-Filename': encodeURIComponent(file.name),
      'X-Knowledge-Visibility': visibility,
      ...(teamId === null ? {} : { 'X-Knowledge-Team-Id': String(teamId) }),
    },
  })

export const retryKnowledgeDocument = (documentId: string) =>
  apiRequest<KnowledgeDocumentDetail>(`/api/knowledge/documents/${documentId}/retry`, {
    method: 'POST',
  })

export const deleteKnowledgeDocument = (documentId: string) =>
  apiRequest<void>(`/api/knowledge/documents/${documentId}`, { method: 'DELETE' })

export const askKnowledgeBase = (question: string) =>
  apiRequest<KnowledgeAnswer>('/api/knowledge/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  })

export const listRagEvaluationCases = () =>
  apiRequest<RagEvaluationCase[]>('/api/knowledge/evaluation-cases')

export const createRagEvaluationCase = (question: string, expectedDocumentIds: string[]) =>
  apiRequest<RagEvaluationCase>('/api/knowledge/evaluation-cases', {
    method: 'POST',
    body: JSON.stringify({ question, expected_document_ids: expectedDocumentIds }),
  })

export const deleteRagEvaluationCase = (caseId: number) =>
  apiRequest<void>(`/api/knowledge/evaluation-cases/${caseId}`, { method: 'DELETE' })

export const listRagEvaluationRuns = () =>
  apiRequest<RagEvaluationRun[]>('/api/knowledge/evaluation-runs')

export const runRagEvaluation = () =>
  apiRequest<RagEvaluationRun>('/api/knowledge/evaluation-runs', { method: 'POST' })
