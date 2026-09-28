import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  askKnowledgeBase,
  createRagEvaluationCase,
  deleteRagEvaluationCase,
  deleteKnowledgeDocument,
  getKnowledgeDocument,
  listKnowledgeDocuments,
  listRagEvaluationCases,
  listRagEvaluationRuns,
  retryKnowledgeDocument,
  runRagEvaluation,
  uploadKnowledgeDocument,
} from '@/services/knowledge'


describe('knowledge service', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uploads, lists, reads, retries, and deletes knowledge documents', async () => {
    const document = {
      id: 'document-1',
      owner_user_id: 1,
      owner_name: '测试教练',
      team_id: null,
      team_name: null,
      original_filename: 'rules.txt',
      content_type: 'text/plain',
      size_bytes: 12,
      visibility: 'platform',
      status: 'ready',
      parser_name: 'knowledge-parser-v1',
      page_count: 1,
      chunk_count: 1,
      error_message: null,
      created_at: '2026-09-28T00:00:00Z',
      updated_at: '2026-09-28T00:00:00Z',
      chunks: [],
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(document), { status: 201, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify([document]), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(document), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(document), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ answer: '规则回答', citations: [], insufficient_evidence: true, answer_model: 'qwen', embedding_model: 'embedding', prompt_version: 'v1' }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    const file = new File(['规则内容'], 'rules.txt', { type: 'text/plain' })
    await uploadKnowledgeDocument(file, 'platform')
    await listKnowledgeDocuments()
    await getKnowledgeDocument('document-1')
    await retryKnowledgeDocument('document-1')
    await deleteKnowledgeDocument('document-1')
    await askKnowledgeBase('什么是七米球？')

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/knowledge/documents',
      expect.objectContaining({
        method: 'POST',
        body: file,
        headers: expect.objectContaining({
          'X-Knowledge-Visibility': 'platform',
          'X-Original-Filename': 'rules.txt',
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      '/api/knowledge/documents/document-1/retry',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      '/api/knowledge/documents/document-1',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      '/api/knowledge/ask',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ question: '什么是七米球？' }) }),
    )
  })

  it('manages fixed evaluation cases and runs versioned RAG evaluation', async () => {
    const evaluationCase = {
      id: 1,
      question: '什么时候判罚七米球？',
      expected_document_ids: ['document-1'],
      owner_user_id: 1,
      team_id: null,
      is_active: true,
      created_at: '2026-09-28T00:00:00Z',
      updated_at: '2026-09-28T00:00:00Z',
    }
    const run = {
      id: 'run-1',
      run_by_user_id: 1,
      team_id: null,
      embedding_model: 'embedding',
      answer_model: 'qwen',
      prompt_version: 'v1',
      top_k: 5,
      relevance_threshold: 0.3,
      case_count: 1,
      recall_at_k: 1,
      citation_hit_rate: 1,
      ungrounded_answer_rate: 0,
      details: [],
      created_at: '2026-09-28T00:00:00Z',
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([evaluationCase]), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(evaluationCase), { status: 201, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([run]), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(run), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await listRagEvaluationCases()
    await createRagEvaluationCase(evaluationCase.question, ['document-1'])
    await deleteRagEvaluationCase(1)
    await listRagEvaluationRuns()
    await runRagEvaluation()

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/knowledge/evaluation-cases',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ question: evaluationCase.question, expected_document_ids: ['document-1'] }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      '/api/knowledge/evaluation-runs',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
