<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import {
  deleteKnowledgeDocument,
  createRagEvaluationCase,
  deleteRagEvaluationCase,
  askKnowledgeBase,
  getKnowledgeDocument,
  listKnowledgeDocuments,
  listRagEvaluationCases,
  listRagEvaluationRuns,
  runRagEvaluation,
  retryKnowledgeDocument,
  uploadKnowledgeDocument,
  type KnowledgeDocumentDetail,
  type KnowledgeDocumentRecord,
  type KnowledgeAnswer,
  type KnowledgeVisibility,
  type RagEvaluationCase,
  type RagEvaluationRun,
} from '@/services/knowledge'
import { useAuthStore } from '@/stores/auth'
import { listTeams, type TeamRecord } from '@/services/teams'

const authStore = useAuthStore()
const documents = ref<KnowledgeDocumentRecord[]>([])
const selectedDocument = ref<KnowledgeDocumentDetail | null>(null)
const selectedFile = ref<File | null>(null)
const visibility = ref<KnowledgeVisibility>('platform')
const selectedTeamId = ref<number | null>(null)
const teams = ref<TeamRecord[]>([])
const fileInputKey = ref(0)
const loading = ref(false)
const uploading = ref(false)
const activeDocumentId = ref<string | null>(null)
const errorMessage = ref('')
const successMessage = ref('')
const question = ref('')
const answer = ref<KnowledgeAnswer | null>(null)
const asking = ref(false)
const questionError = ref('')
const evaluationCases = ref<RagEvaluationCase[]>([])
const evaluationRuns = ref<RagEvaluationRun[]>([])
const evaluationQuestion = ref('')
const expectedDocumentIds = ref<string[]>([])
const evaluationBusy = ref(false)
const evaluationError = ref('')
const expandedRunId = ref<string | null>(null)

const canManage = computed(() => authStore.hasPermission('manage_knowledge_base'))
const canQuery = computed(() => authStore.hasPermission('query_knowledge_base'))
const canChooseAnyTeam = computed(() =>
  authStore.user?.role === 'competition_admin' || authStore.user?.role === 'system_admin',
)

const statusLabel = (status: KnowledgeDocumentRecord['status']) =>
  ({ processing: '处理中', ready: '可检索', failed: '处理失败' })[status]

const statusClass = (status: KnowledgeDocumentRecord['status']) =>
  status === 'ready' ? 'status-ready' : status === 'failed' ? 'status-failed' : 'status-processing'

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KiB`
  return `${(bytes / 1024 ** 2).toFixed(1)} MiB`
}

const loadDocuments = async () => {
  if (!canManage.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    documents.value = await listKnowledgeDocuments()
    if (selectedDocument.value) {
      const current = documents.value.find((item) => item.id === selectedDocument.value?.id)
      if (!current) selectedDocument.value = null
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识文档加载失败'
  } finally {
    loading.value = false
  }
}

const loadEvaluations = async () => {
  if (!canManage.value) return
  try {
    const [cases, runs] = await Promise.all([listRagEvaluationCases(), listRagEvaluationRuns()])
    evaluationCases.value = cases
    evaluationRuns.value = runs
  } catch (error) {
    evaluationError.value = error instanceof Error ? error.message : '评测记录加载失败'
  }
}

const addEvaluationCase = async () => {
  if (evaluationQuestion.value.trim().length < 2 || expectedDocumentIds.value.length === 0) return
  evaluationBusy.value = true
  evaluationError.value = ''
  try {
    await createRagEvaluationCase(evaluationQuestion.value.trim(), expectedDocumentIds.value)
    evaluationQuestion.value = ''
    expectedDocumentIds.value = []
    await loadEvaluations()
  } catch (error) {
    evaluationError.value = error instanceof Error ? error.message : '固定评测问题保存失败'
  } finally {
    evaluationBusy.value = false
  }
}

const removeEvaluationCase = async (caseId: number) => {
  evaluationBusy.value = true
  evaluationError.value = ''
  try {
    await deleteRagEvaluationCase(caseId)
    await loadEvaluations()
  } catch (error) {
    evaluationError.value = error instanceof Error ? error.message : '评测问题删除失败'
  } finally {
    evaluationBusy.value = false
  }
}

const startEvaluation = async () => {
  evaluationBusy.value = true
  evaluationError.value = ''
  try {
    const run = await runRagEvaluation()
    await loadEvaluations()
    expandedRunId.value = run.id
  } catch (error) {
    evaluationError.value = error instanceof Error ? error.message : 'RAG 评测执行失败'
  } finally {
    evaluationBusy.value = false
  }
}

const chooseFile = (event: Event) => {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

const uploadDocument = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const uploaded = await uploadKnowledgeDocument(
      selectedFile.value,
      visibility.value,
      visibility.value === 'team_private' ? selectedTeamId.value : null,
    )
    selectedDocument.value = uploaded
    selectedFile.value = null
    fileInputKey.value += 1
    successMessage.value = uploaded.status === 'ready'
      ? `“${uploaded.original_filename}”已解析为 ${uploaded.chunk_count} 个可检索分块。`
      : '文件已保存，但解析失败；可以查看原因后重试或删除。'
    await loadDocuments()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识文档上传失败'
  } finally {
    uploading.value = false
  }
}

const inspectDocument = async (document: KnowledgeDocumentRecord) => {
  activeDocumentId.value = document.id
  errorMessage.value = ''
  try {
    selectedDocument.value = await getKnowledgeDocument(document.id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档详情加载失败'
  } finally {
    activeDocumentId.value = null
  }
}

const retryDocument = async (document: KnowledgeDocumentRecord) => {
  activeDocumentId.value = document.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const updated = await retryKnowledgeDocument(document.id)
    selectedDocument.value = updated
    successMessage.value = updated.status === 'ready'
      ? '重新处理成功。'
      : `重新处理仍然失败：${updated.error_message ?? '未知原因'}`
    await loadDocuments()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '重新处理失败'
  } finally {
    activeDocumentId.value = null
  }
}

const removeDocument = async (document: KnowledgeDocumentRecord) => {
  if (!window.confirm(`确认删除“${document.original_filename}”及其全部文本分块吗？`)) return
  activeDocumentId.value = document.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await deleteKnowledgeDocument(document.id)
    if (selectedDocument.value?.id === document.id) selectedDocument.value = null
    successMessage.value = '知识文档及其分块已删除。'
    await loadDocuments()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识文档删除失败'
  } finally {
    activeDocumentId.value = null
  }
}

const askQuestion = async () => {
  const normalized = question.value.trim()
  if (normalized.length < 2) return
  asking.value = true
  questionError.value = ''
  answer.value = null
  try {
    answer.value = await askKnowledgeBase(normalized)
  } catch (error) {
    questionError.value = error instanceof Error ? error.message : '知识库回答失败'
  } finally {
    asking.value = false
  }
}

const inspectCitation = async (documentId: string) => {
  if (!canManage.value) return
  const document = documents.value.find((item) => item.id === documentId)
  if (document) await inspectDocument(document)
}

watch(
  [() => authStore.initialized, canManage],
  ([initialized, allowed]) => {
    if (initialized && allowed) void loadDocuments()
    if (initialized && allowed) void loadEvaluations()
    if (initialized && (allowed || canQuery.value)) {
      selectedTeamId.value ??= authStore.user?.team_id ?? null
      void listTeams().then((records) => { teams.value = records })
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container knowledge-page">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Knowledge center</p>
          <h1>手球资料库</h1>
          <p class="page-description">
            从资料上传、内容解析到有依据的问答，在一个连续流程中管理规则、赛事规程、战术和内部资料。
          </p>
        </div>
      </header>

      <section v-if="!canManage && !canQuery" class="panel empty-state">
        当前账号没有资料库访问权限。
      </section>

      <template v-else>
        <section class="knowledge-flow" aria-label="资料库使用流程">
          <div v-if="canManage" class="flow-item">
            <span>01</span>
            <strong>上传资料</strong>
            <small>添加规则、规程与内部文档</small>
          </div>
          <div v-if="canManage" class="flow-item">
            <span>02</span>
            <strong>检查解析</strong>
            <small>确认页码、章节与文本分块</small>
          </div>
          <div v-if="canQuery" class="flow-item">
            <span>{{ canManage ? '03' : '01' }}</span>
            <strong>检索提问</strong>
            <small>获得带原文出处的回答</small>
          </div>
        </section>

        <section v-if="canManage" class="panel workflow-panel upload-panel">
          <div class="workflow-heading">
            <span class="step-number">01</span>
            <div>
              <p class="eyebrow">Add source material</p>
            <h2 class="section-title">上传资料</h2>
              <p>先添加可检索的原始资料。支持带文本层的 PDF、UTF-8 TXT 和 Markdown，单个文件最大 20 MiB。</p>
            </div>
          </div>
          <div class="upload-controls">
            <label class="file-field">
              选择文档
              <input
                :key="fileInputKey"
                type="file"
                accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                @change="chooseFile"
              />
            </label>
            <label>
              可见范围
              <select v-model="visibility">
                <option value="platform">资料库用户可见</option>
                <option value="team_private" :disabled="!canChooseAnyTeam && authStore.user?.team_id === null">
                  所属球队可见
                </option>
                <option value="owner_private">仅上传者和管理员可见</option>
              </select>
            </label>
            <label v-if="visibility === 'team_private'">
              关联球队
              <select v-model="selectedTeamId" :disabled="!canChooseAnyTeam">
                <option :value="null">请选择球队</option>
                <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
              </select>
            </label>
            <button
              class="button button-primary"
              type="button"
              :disabled="!selectedFile || uploading || (visibility === 'team_private' && selectedTeamId === null)"
              @click="uploadDocument"
            >
              {{ uploading ? '正在解析…' : '上传并解析' }}
            </button>
          </div>
          <p v-if="selectedFile" class="selected-file">
            已选择 {{ selectedFile.name }} · {{ formatBytes(selectedFile.size) }}
          </p>
        </section>

        <p v-if="successMessage" class="message success">{{ successMessage }}</p>
        <p v-if="errorMessage" class="message error">{{ errorMessage }}</p>

        <section v-if="canManage" class="workflow-section">
          <div class="workflow-heading section-workflow-heading">
            <span class="step-number">02</span>
            <div>
              <p class="eyebrow">Review and verify</p>
              <h2 class="section-title">检查资料与解析结果</h2>
              <p>确认文档已成功解析，并抽查页码、章节和文本内容是否正确。</p>
            </div>
          </div>
          <div class="knowledge-layout">
          <div class="panel document-panel">
            <div class="panel-heading">
              <div>
                <h2 class="section-title">已上传文档</h2>
              </div>
              <span>{{ documents.length }} 份</span>
            </div>
            <div v-if="loading" class="empty-state">正在加载文档…</div>
            <div v-else-if="documents.length === 0" class="empty-state">
              还没有知识文档，可以先上传一份手球规则或战术资料。
            </div>
            <ul v-else class="document-list">
              <li
                v-for="document in documents"
                :key="document.id"
                :class="{ selected: selectedDocument?.id === document.id }"
              >
                <button class="document-main" type="button" @click="inspectDocument(document)">
                  <strong>{{ document.original_filename }}</strong>
                  <span>
                    {{ document.owner_name }} · {{ formatBytes(document.size_bytes) }} ·
                    {{ document.chunk_count }} 个分块
                  </span>
                  <small>
                    {{ document.visibility === 'platform' ? '资料库用户可见' : document.visibility === 'team_private' ? `${document.team_name ?? '球队'}可见` : '仅上传者和管理员可见' }}
                  </small>
                </button>
                <div class="document-actions">
                  <span class="status-badge" :class="statusClass(document.status)">
                    {{ statusLabel(document.status) }}
                  </span>
                  <button
                    v-if="document.status === 'failed'"
                    class="button button-secondary"
                    type="button"
                    :disabled="activeDocumentId === document.id"
                    @click="retryDocument(document)"
                  >
                    重试
                  </button>
                  <button
                    class="button button-danger"
                    type="button"
                    :disabled="activeDocumentId === document.id"
                    @click="removeDocument(document)"
                  >
                    删除
                  </button>
                </div>
                <p v-if="document.error_message" class="document-error">
                  {{ document.error_message }}
                </p>
              </li>
            </ul>
          </div>

          <aside class="panel chunk-panel">
            <template v-if="selectedDocument">
              <div class="panel-heading">
                <div>
                  <h2 class="section-title">解析结果</h2>
                </div>
                <span>{{ selectedDocument.chunk_count }} 块</span>
              </div>
              <p class="chunk-summary">
                {{ selectedDocument.original_filename }} · 解析器 {{ selectedDocument.parser_name }}
              </p>
              <div v-if="selectedDocument.status === 'failed'" class="failed-detail">
                <strong>处理失败</strong>
                <p>{{ selectedDocument.error_message }}</p>
              </div>
              <ol v-else class="chunk-list">
                <li v-for="chunk in selectedDocument.chunks" :key="chunk.id">
                  <div>
                    <strong>分块 {{ chunk.ordinal }}</strong>
                    <span v-if="chunk.page_number">第 {{ chunk.page_number }} 页</span>
                    <span v-else-if="chunk.section_title">{{ chunk.section_title }}</span>
                  </div>
                  <p>{{ chunk.content }}</p>
                </li>
              </ol>
            </template>
            <div v-else class="empty-state">点击左侧文档查看分块内容和来源。</div>
          </aside>
          </div>
        </section>

        <section v-if="canQuery" class="panel workflow-panel question-panel">
          <div class="workflow-heading">
            <span class="step-number">{{ canManage ? '03' : '01' }}</span>
            <div>
              <p class="eyebrow">Ask with evidence</p>
              <h2 class="section-title">向资料库提问</h2>
              <p>系统只根据已上传文档回答，并展示文档名、页码或章节和引用片段。</p>
            </div>
          </div>
          <form class="question-form" @submit.prevent="askQuestion">
            <textarea
              v-model="question"
              rows="3"
              maxlength="2000"
              placeholder="例如：手球比赛中，什么情况下会判罚七米球？"
            />
            <button class="button button-primary" type="submit" :disabled="asking || question.trim().length < 2">
              {{ asking ? '正在检索并回答…' : '提问' }}
            </button>
          </form>
          <p v-if="questionError" class="message error">{{ questionError }}</p>
          <article v-if="answer" class="answer-card" :class="{ insufficient: answer.insufficient_evidence }">
            <div class="answer-heading">
              <strong>{{ answer.insufficient_evidence ? '未找到可靠依据' : '资料库回答' }}</strong>
              <span>{{ answer.answer_model }} · {{ answer.embedding_model }}</span>
            </div>
            <p>{{ answer.answer }}</p>
            <div v-if="answer.citations.length" class="citation-list">
              <strong>引用来源</strong>
              <button
                v-for="citation in answer.citations"
                :key="citation.chunk_id"
                type="button"
                @click="inspectCitation(citation.document_id)"
              >
                <span>
                  {{ citation.document_name }}
                  <template v-if="citation.page_number">· 第 {{ citation.page_number }} 页</template>
                  <template v-else-if="citation.section_title">· {{ citation.section_title }}</template>
                  · 相关度 {{ (citation.score * 100).toFixed(1) }}%
                </span>
                <small>{{ citation.excerpt }}</small>
              </button>
            </div>
          </article>
        </section>

        <section v-if="canManage" class="panel evaluation-panel">
          <div class="panel-heading">
            <div>
              <p class="eyebrow">Quality control</p>
              <h2 class="section-title">固定问题集与自动评测</h2>
              <p>给问题指定正确来源，系统保存每次评测的模型配置、检索分数和引用结果。</p>
            </div>
            <button
              class="button button-primary"
              type="button"
              :disabled="evaluationBusy || evaluationCases.length === 0"
              @click="startEvaluation"
            >
              {{ evaluationBusy ? '执行中…' : '运行评测' }}
            </button>
          </div>
          <div class="evaluation-form">
            <label>
              固定问题
              <input v-model="evaluationQuestion" maxlength="2000" placeholder="例如：什么情况下判罚七米球？" />
            </label>
            <label>
              正确来源（可多选）
              <select v-model="expectedDocumentIds" multiple>
                <option v-for="document in documents.filter((item) => item.status === 'ready')" :key="document.id" :value="document.id">
                  {{ document.original_filename }}
                </option>
              </select>
            </label>
            <button
              class="button button-secondary"
              type="button"
              :disabled="evaluationBusy || evaluationQuestion.trim().length < 2 || expectedDocumentIds.length === 0"
              @click="addEvaluationCase"
            >
              加入固定问题集
            </button>
          </div>
          <p v-if="evaluationError" class="message error">{{ evaluationError }}</p>
          <div class="evaluation-grid">
            <div>
              <h3>固定问题（{{ evaluationCases.length }}）</h3>
              <div v-if="evaluationCases.length === 0" class="empty-state">还没有评测问题。</div>
              <ul v-else class="evaluation-case-list">
                <li v-for="item in evaluationCases" :key="item.id">
                  <div>
                    <strong>{{ item.question }}</strong>
                    <span>正确来源 {{ item.expected_document_ids.length }} 份</span>
                  </div>
                  <button type="button" :disabled="evaluationBusy" @click="removeEvaluationCase(item.id)">删除</button>
                </li>
              </ul>
            </div>
            <div>
              <h3>历史结果（{{ evaluationRuns.length }}）</h3>
              <div v-if="evaluationRuns.length === 0" class="empty-state">运行后会在这里保留版本化结果。</div>
              <template v-else>
                <article v-for="run in evaluationRuns" :key="run.id" class="evaluation-run">
                  <button type="button" @click="expandedRunId = expandedRunId === run.id ? null : run.id">
                    <strong>{{ new Date(run.created_at).toLocaleString() }} · {{ run.prompt_version }}</strong>
                    <span>
                      Recall@{{ run.top_k }} {{ (run.recall_at_k * 100).toFixed(1) }}% ·
                      引用命中 {{ (run.citation_hit_rate * 100).toFixed(1) }}% ·
                      无依据 {{ (run.ungrounded_answer_rate * 100).toFixed(1) }}%
                    </span>
                  </button>
                  <div v-if="expandedRunId === run.id" class="evaluation-details">
                    <p>{{ run.answer_model }} · {{ run.embedding_model }} · 阈值 {{ run.relevance_threshold }}</p>
                    <div v-for="detail in run.details" :key="detail.case_id">
                      <strong>{{ detail.question }}</strong>
                      <span>Recall {{ (detail.recall_at_k * 100).toFixed(1) }}% · 引用命中 {{ (detail.citation_hit_rate * 100).toFixed(1) }}%</span>
                      <small>{{ detail.answer }}</small>
                    </div>
                  </div>
                </article>
              </template>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.knowledge-page { max-width: 1392px; padding-top: 48px; }
.knowledge-page > .page-heading { margin-bottom: 28px; }
.knowledge-page > .page-heading h1 { font-size: clamp(36px, 5vw, 58px); letter-spacing: -.045em; }
.knowledge-page > .page-heading .page-description { max-width: 820px; font-size: 16px; line-height: 1.8; }

.knowledge-flow { position: relative; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 22px; }
.flow-item { position: relative; display: grid; min-height: 112px; align-content: center; gap: 4px; padding: 20px 22px 20px 66px; border: 1px solid var(--border); border-radius: 16px; background: rgba(10, 21, 36, .72); backdrop-filter: blur(16px); }
.flow-item > span { position: absolute; top: 20px; left: 20px; color: #6fa7ff; font-size: 12px; font-weight: 800; letter-spacing: .12em; }
.flow-item strong { font-size: 16px; }
.flow-item small { color: var(--muted-strong); line-height: 1.55; }

.workflow-panel { position: relative; display: grid; gap: 22px; margin-bottom: 22px; overflow: hidden; }
.workflow-panel::before { position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: linear-gradient(90deg, #125bf0, #5f9dff 45%, transparent 88%); content: ''; }
.workflow-heading { display: flex; align-items: flex-start; gap: 16px; }
.workflow-heading > div { min-width: 0; }
.workflow-heading .section-title { margin-bottom: 5px; font-size: 22px; }
.workflow-heading p { margin: 0; color: var(--muted-strong); }
.workflow-heading .eyebrow { margin-bottom: 6px; color: #6fa7ff; }
.step-number { display: grid; width: 42px; height: 42px; flex: 0 0 auto; place-items: center; border: 1px solid rgba(95, 157, 255, .4); border-radius: 13px; color: #9dc2ff; background: rgba(18, 91, 240, .15); font-size: 12px; font-weight: 850; letter-spacing: .08em; }
.workflow-section { margin: 34px 0 22px; }
.section-workflow-heading { margin: 0 0 16px 2px; }
.section-workflow-heading p { margin: 0; color: var(--muted-strong); }

.question-form { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 12px; }
.question-form textarea { width: 100%; min-height: 92px; padding: 15px 16px; border: 1px solid var(--border); border-radius: 14px; outline: none; color: var(--ink); background: var(--surface-soft); resize: vertical; }
.question-form textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-soft); }
.answer-card { display: grid; gap: 14px; padding: 20px; border: 1px solid rgba(95, 157, 255, .38); border-radius: 16px; background: rgba(18, 91, 240, .09); }
.answer-card.insufficient { border-color: rgba(230, 171, 69, .4); background: rgba(179, 117, 18, .1); }
.answer-heading { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.answer-heading span { color: var(--muted); font-size: 12px; }
.answer-card > p { margin: 0; color: var(--ink); line-height: 1.78; white-space: pre-wrap; }
.citation-list { display: grid; gap: 8px; }
.citation-list > button { display: grid; gap: 5px; padding: 13px 14px; border: 1px solid var(--border); border-radius: 12px; color: var(--ink); background: rgba(8, 18, 31, .72); text-align: left; cursor: pointer; }
.citation-list > button:hover { border-color: var(--border-strong); background: var(--surface-muted); }
.citation-list span { color: #85b4ff; font-size: 13px; font-weight: 750; }
.citation-list small { color: var(--muted-strong); line-height: 1.55; }

.upload-controls { display: grid; grid-template-columns: minmax(280px, 1.4fr) minmax(220px, .8fr) auto; align-items: end; gap: 14px; }
.upload-controls label { display: grid; gap: 7px; color: var(--muted-strong); font-size: 12px; font-weight: 700; }
.upload-controls input,
.upload-controls select { width: 100%; min-height: 44px; padding: 9px 12px; border: 1px solid var(--border); border-radius: 11px; color: var(--ink); background: var(--surface-soft); }
.selected-file { margin: -8px 0 0; color: #8fbaff; font-size: 13px; }
.message { margin: 14px 0 0; padding: 12px 14px; border-radius: 12px; }
.message.success { color: var(--success); background: var(--success-soft); }
.message.error { color: var(--danger); background: var(--danger-soft); }

.knowledge-layout { display: grid; grid-template-columns: minmax(420px, .95fr) minmax(0, 1.05fr); gap: 16px; }
.document-panel,
.chunk-panel { min-height: 420px; }
.panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.panel-heading > span { color: var(--muted); font-size: 13px; }
.document-list,
.chunk-list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
.document-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px 14px; padding: 14px; border: 1px solid var(--border); border-radius: 12px; background: rgba(7, 16, 29, .38); }
.document-list li.selected { border-color: rgba(95, 157, 255, .65); background: var(--primary-soft); }
.document-main { display: grid; gap: 5px; padding: 0; color: var(--ink); text-align: left; background: transparent; cursor: pointer; }
.document-main span,
.document-main small,
.chunk-summary { color: var(--muted-strong); }
.document-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 7px; }
.document-actions .button { min-height: 34px; padding: 0 10px; }
.document-error { grid-column: 1 / -1; margin: 0; color: var(--danger); font-size: 13px; }
.chunk-panel { max-height: 760px; overflow: auto; }
.chunk-summary { margin: 0 0 14px; font-size: 13px; }
.chunk-list li { padding: 14px; border: 1px solid var(--border); border-radius: 12px; background: rgba(7, 16, 29, .55); }
.chunk-list li > div { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.chunk-list span { color: #85b4ff; font-size: 12px; font-weight: 700; }
.chunk-list p { margin: 10px 0 0; color: var(--muted-strong); line-height: 1.65; white-space: pre-wrap; }
.failed-detail { padding: 16px; border: 1px solid rgba(255, 82, 96, .4); border-radius: 12px; color: var(--danger); background: var(--danger-soft); }
.failed-detail p { margin: 7px 0 0; }

.evaluation-panel { display: grid; gap: 18px; margin-top: 22px; }
.evaluation-panel .panel-heading p { margin: 6px 0 0; color: var(--muted-strong); }
.evaluation-form { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(240px, .7fr) auto; align-items: end; gap: 12px; }
.evaluation-form label { display: grid; gap: 7px; color: var(--muted-strong); font-size: 12px; font-weight: 700; }
.evaluation-form input,
.evaluation-form select { min-height: 42px; padding: 9px 12px; border: 1px solid var(--border); border-radius: 10px; color: var(--ink); background: var(--surface-soft); }
.evaluation-form select { min-height: 88px; }
.evaluation-grid { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr); gap: 18px; }
.evaluation-grid h3 { margin: 0 0 10px; font-size: 15px; }
.evaluation-case-list { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.evaluation-case-list li { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px; border: 1px solid var(--border); border-radius: 10px; }
.evaluation-case-list li > div { display: grid; gap: 4px; }
.evaluation-case-list span { color: var(--muted); font-size: 12px; }
.evaluation-case-list button { color: var(--danger); background: transparent; cursor: pointer; }
.evaluation-run { margin-bottom: 8px; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.evaluation-run > button { display: grid; gap: 5px; width: 100%; padding: 12px; color: var(--ink); background: var(--surface-soft); text-align: left; cursor: pointer; }
.evaluation-run > button span { color: var(--muted-strong); font-size: 12px; }
.evaluation-details { display: grid; gap: 8px; padding: 12px; border-top: 1px solid var(--border); background: rgba(7, 16, 29, .48); }
.evaluation-details > p { margin: 0; color: var(--muted); font-size: 12px; }
.evaluation-details > div { display: grid; gap: 4px; padding: 9px; border-radius: 8px; background: var(--surface-soft); }
.evaluation-details span,
.evaluation-details small { color: var(--muted-strong); }

@media (max-width: 900px) {
  .knowledge-flow { grid-template-columns: 1fr; }
  .question-form,
  .upload-controls,
  .knowledge-layout,
  .evaluation-form,
  .evaluation-grid { grid-template-columns: 1fr; }
  .chunk-panel { max-height: none; }
}
@media (max-width: 620px) {
  .knowledge-page { padding-top: 30px; }
  .workflow-heading { gap: 12px; }
  .document-list li { grid-template-columns: 1fr; }
  .document-actions { justify-content: flex-start; }
  .answer-heading { align-items: flex-start; flex-direction: column; }
}
</style>
