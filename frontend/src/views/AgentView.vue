<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import {
  confirmAgentProposal,
  createAgentSession,
  deleteAgentSession,
  getAgentSession,
  listAgentSessions,
  rejectAgentProposal,
  retryAgentRun,
  sendAgentMessage,
  type AgentActionProposal,
  type AgentMessage,
  type AgentRun,
  type AgentSession,
  type AgentSessionDetail,
} from '@/services/agent'
import { listMatches, type MatchRecord } from '@/services/matches'
import { listTeams, type TeamRecord } from '@/services/teams'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const sessions = ref<AgentSession[]>([])
const current = ref<AgentSessionDetail | null>(null)
const matches = ref<MatchRecord[]>([])
const teams = ref<TeamRecord[]>([])
const newMatchId = ref<number | null>(null)
const input = ref('')
const loading = ref(false)
const sending = ref(false)
const actionBusyId = ref<string | null>(null)
const errorMessage = ref('')
const chatEnd = ref<HTMLElement | null>(null)

const canUseAgent = computed(() => authStore.hasPermission('use_match_agent'))
const teamNames = computed(() => new Map(teams.value.map((team) => [team.id, team.name])))

const matchLabel = (match: MatchRecord) =>
  `${match.match_date} · ${teamNames.value.get(match.home_team_id) ?? '主队'} vs ${teamNames.value.get(match.away_team_id) ?? '客队'}`

const toolLabels: Record<string, string> = {
  get_match_overview: '读取比赛概况',
  get_match_events: '读取已确认事件',
  get_player_stats: '读取球员官方统计',
  search_handball_knowledge: '检索手球资料',
  propose_update_match_status: '生成比赛状态修改计划',
}

const toolStatusLabel = (status: string) =>
  ({ running: '执行中', completed: '成功', failed: '失败', denied: '已拒绝' })[status] ?? status

const runForMessage = (message: AgentMessage) =>
  current.value?.runs.find((run) => run.assistant_message_id === message.id) ?? null

const scrollToEnd = async () => {
  await nextTick()
  chatEnd.value?.scrollIntoView({ behavior: 'smooth', block: 'end' })
}

const loadSessions = async () => {
  if (!canUseAgent.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    sessions.value = await listAgentSessions()
    if (!current.value && sessions.value.length) {
      current.value = await getAgentSession(sessions.value[0]!.id)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Agent 会话加载失败'
  } finally {
    loading.value = false
  }
}

const openSession = async (session: AgentSession) => {
  loading.value = true
  errorMessage.value = ''
  try {
    current.value = await getAgentSession(session.id)
    await scrollToEnd()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '会话加载失败'
  } finally {
    loading.value = false
  }
}

const newSession = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    current.value = await createAgentSession(newMatchId.value)
    await loadSessions()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '会话创建失败'
  } finally {
    loading.value = false
  }
}

const removeSession = async () => {
  if (!current.value || !window.confirm('删除该会话及其全部短期记忆和工具轨迹吗？')) return
  loading.value = true
  try {
    await deleteAgentSession(current.value.session.id)
    current.value = null
    await loadSessions()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '会话删除失败'
  } finally {
    loading.value = false
  }
}

const send = async () => {
  if (!current.value || input.value.trim().length === 0) return
  sending.value = true
  errorMessage.value = ''
  const content = input.value.trim()
  input.value = ''
  try {
    await sendAgentMessage(current.value.session.id, content)
    current.value = await getAgentSession(current.value.session.id)
    await loadSessions()
    await scrollToEnd()
  } catch (error) {
    input.value = content
    errorMessage.value = error instanceof Error ? error.message : 'Agent 回答失败'
  } finally {
    sending.value = false
  }
}

const retry = async (run: AgentRun) => {
  if (!current.value) return
  sending.value = true
  errorMessage.value = ''
  try {
    await retryAgentRun(run.id)
    current.value = await getAgentSession(current.value.session.id)
    await scrollToEnd()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '重试失败'
  } finally {
    sending.value = false
  }
}

const updateProposal = (updated: AgentActionProposal) => {
  if (!current.value) return
  for (const run of current.value.runs) {
    run.proposals = run.proposals.map((proposal) => proposal.id === updated.id ? updated : proposal)
  }
}

const confirmProposal = async (proposal: AgentActionProposal) => {
  if (!window.confirm(`确认执行：${proposal.summary}？后端会重新检查你的权限。`)) return
  actionBusyId.value = proposal.id
  errorMessage.value = ''
  try {
    updateProposal(await confirmAgentProposal(proposal.id))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '写操作确认失败'
  } finally {
    actionBusyId.value = null
  }
}

const rejectProposal = async (proposal: AgentActionProposal) => {
  actionBusyId.value = proposal.id
  try {
    updateProposal(await rejectAgentProposal(proposal.id))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '计划取消失败'
  } finally {
    actionBusyId.value = null
  }
}

watch(
  [() => authStore.initialized, canUseAgent],
  ([initialized, allowed]) => {
    if (!initialized || !allowed) return
    void Promise.all([listMatches(), listTeams()]).then(([matchRows, teamRows]) => {
      matches.value = matchRows
      teams.value = teamRows
    })
    void loadSessions()
  },
  { immediate: true },
)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container agent-page">
      <header class="page-heading">
        <div>
          <h1>比赛分析</h1>
          <p class="page-description">查询比赛、已确认事件、官方球员统计和资料库内容。</p>
        </div>
      </header>

      <section v-if="!canUseAgent" class="panel empty-state">当前账号没有使用比赛分析的权限。</section>

      <section v-else class="agent-layout">
        <aside class="panel session-sidebar">
          <div class="new-session">
            <label>
              新会话关联比赛
              <select v-model="newMatchId">
                <option :value="null">暂不选择比赛</option>
                <option v-for="match in matches" :key="match.id" :value="match.id">{{ matchLabel(match) }}</option>
              </select>
            </label>
            <button class="button button-primary" type="button" :disabled="loading" @click="newSession">新建会话</button>
          </div>
          <div class="session-heading">
            <strong>历史会话</strong>
            <span>{{ sessions.length }}</span>
          </div>
          <div v-if="loading && sessions.length === 0" class="empty-state compact">正在加载…</div>
          <div v-else-if="sessions.length === 0" class="empty-state compact">还没有分析会话。</div>
          <template v-else>
            <button
              v-for="session in sessions"
              :key="session.id"
              class="session-item"
              :class="{ active: current?.session.id === session.id }"
              type="button"
              @click="openSession(session)"
            >
              <strong>{{ session.title }}</strong>
              <span>{{ session.match_label ?? '未选择比赛' }}</span>
              <small>{{ new Date(session.updated_at).toLocaleString() }}</small>
            </button>
          </template>
        </aside>

        <section class="panel chat-panel">
          <template v-if="current">
            <header class="chat-header">
              <div>
                <strong>{{ current.session.title }}</strong>
                <span>{{ current.session.match_label ?? '尚未指定比赛' }}</span>
              </div>
              <button class="button button-danger" type="button" :disabled="loading || sending" @click="removeSession">删除会话</button>
            </header>

            <div class="message-list">
              <div v-if="current.messages.length === 0" class="empty-state">
                <strong>可以这样提问</strong>
                <p>“谁的进球最多？”、“第 10 分钟发生了什么？”、“他们下半场的表现呢？”</p>
              </div>
              <article v-for="message in current.messages" :key="message.id" class="message-row" :class="message.role">
                <div class="message-bubble">
                  <span class="message-role">{{ message.role === 'user' ? '你' : '分析结果' }}</span>
                  <p>{{ message.content }}</p>
                  <details v-if="message.sources.length" class="source-details">
                    <summary>
                      <span>数据来源</span>
                      <small>{{ message.sources.length }} 项</small>
                    </summary>
                    <div class="source-list">
                      <RouterLink
                        v-for="source in message.sources"
                        :key="source.id"
                        :to="source.match_id ? { name: 'match-detail', params: { matchId: source.match_id } } : '/knowledge'"
                      >
                        <span>{{ source.label }}</span>
                        <small v-if="source.timestamp_seconds !== null">视频时间 {{ Math.floor(source.timestamp_seconds / 60) }}:{{ String(Math.floor(source.timestamp_seconds % 60)).padStart(2, '0') }}</small>
                        <small v-else-if="source.excerpt">{{ source.excerpt }}</small>
                      </RouterLink>
                    </div>
                  </details>

                  <template v-if="message.role === 'assistant' && runForMessage(message)">
                    <details class="run-details">
                      <summary>
                        执行详情 · {{ runForMessage(message)?.tool_calls.length ?? 0 }} 个工具 ·
                        {{ runForMessage(message)?.latency_ms ?? 0 }} ms
                      </summary>
                      <div class="run-meta">
                        {{ runForMessage(message)?.model_name }} · {{ runForMessage(message)?.prompt_version }}
                      </div>
                      <ol v-if="runForMessage(message)?.tool_calls.length" class="tool-list">
                        <li v-for="call in runForMessage(message)?.tool_calls" :key="call.id" :class="`tool-${call.status}`">
                          <div>
                            <strong>{{ toolLabels[call.tool_name] ?? call.tool_name }}</strong>
                            <span>{{ toolStatusLabel(call.status) }} · {{ call.duration_ms }} ms</span>
                          </div>
                          <code>{{ JSON.stringify(call.arguments_summary) }}</code>
                          <p v-if="call.error_message">{{ call.error_message }}{{ call.retryable ? '（可重试）' : '' }}</p>
                        </li>
                      </ol>
                      <button
                        v-if="runForMessage(message)?.status === 'failed'"
                        class="button button-secondary"
                        type="button"
                        :disabled="sending"
                        @click="retry(runForMessage(message)!)"
                      >
                        重试本次分析
                      </button>
                    </details>

                    <div v-for="proposal in runForMessage(message)?.proposals" :key="proposal.id" class="proposal-card">
                      <div>
                        <strong>待确认写操作</strong>
                        <span :class="`proposal-${proposal.status}`">{{ proposal.status }}</span>
                      </div>
                      <p>{{ proposal.summary }}</p>
                      <div v-if="proposal.status === 'pending'" class="proposal-actions">
                        <button class="button button-primary" type="button" :disabled="actionBusyId === proposal.id" @click="confirmProposal(proposal)">确认执行</button>
                        <button class="button button-secondary" type="button" :disabled="actionBusyId === proposal.id" @click="rejectProposal(proposal)">取消计划</button>
                      </div>
                    </div>
                  </template>
                </div>
              </article>
              <div v-if="sending" class="message-row assistant"><div class="message-bubble thinking">正在整理比赛数据…</div></div>
              <div ref="chatEnd" />
            </div>

            <p v-if="errorMessage" class="agent-error">{{ errorMessage }}</p>
            <form class="composer" @submit.prevent="send">
              <textarea v-model="input" rows="2" maxlength="4000" placeholder="询问这场比赛、球员表现、事件时间点或手球规则…" @keydown.meta.enter.prevent="send" />
              <button class="button button-primary" type="submit" :disabled="sending || input.trim().length === 0">{{ sending ? '分析中…' : '发送' }}</button>
            </form>
          </template>
          <div v-else class="empty-state chat-empty">
            <strong>选择或新建一个会话</strong>
            <p>建议先关联一场比赛，这样追问“他们”“下半场”等表达时上下文更准确。</p>
          </div>
        </section>
      </section>
    </main>
  </div>
</template>

<style scoped>
.agent-page { max-width: 1440px; }
.agent-layout { display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 18px; align-items: stretch; }
.session-sidebar { display: flex; min-height: 760px; flex-direction: column; gap: 8px; padding: 18px; }
.new-session { display: grid; gap: 10px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
.new-session label { display: grid; gap: 7px; color: var(--muted-strong); font-size: 12px; font-weight: 700; }
.new-session select { width: 100%; min-height: 46px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 11px; background: var(--surface-soft); }
.session-heading { display: flex; align-items: center; justify-content: space-between; margin: 5px 2px; }
.session-heading span { color: var(--muted); font-size: 12px; }
.session-item { display: grid; gap: 5px; width: 100%; padding: 13px; border: 1px solid transparent; border-radius: 12px; color: var(--ink); background: transparent; text-align: left; cursor: pointer; }
.session-item:hover,
.session-item.active { border-color: var(--border); background: var(--primary-soft); }
.session-item strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-item span,
.session-item small { color: var(--muted); font-size: 12px; }
.empty-state.compact { padding: 22px 8px; }
.chat-panel { display: grid; min-height: 760px; grid-template-rows: auto minmax(0, 1fr) auto auto; padding: 0; overflow: hidden; }
.chat-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 24px; border-bottom: 1px solid var(--border); }
.chat-header > div { display: grid; gap: 4px; }
.chat-header span { color: var(--muted); font-size: 12px; }
.message-list { min-height: 0; max-height: 700px; padding: 24px; overflow-y: auto; background: white; }
.message-row { display: flex; margin-bottom: 16px; }
.message-row.user { justify-content: flex-end; }
.message-bubble { width: min(840px, 88%); padding: 18px; border: 1px solid #dbe5f1; border-radius: 16px; background: var(--surface-soft); }
.message-row.user .message-bubble { padding: 14px 16px; border: 0; border-radius: 16px; color: white; background: var(--primary); }
.message-role { display: block; margin-bottom: 7px; color: var(--primary-dark); font-size: 11px; font-weight: 800; text-transform: uppercase; }
.message-row.user .message-role { color: #d7e4ff; }
.message-bubble > p { margin: 0; line-height: 1.72; white-space: pre-wrap; }
.message-bubble.thinking { color: var(--muted-strong); font-size: 13px; }
.source-details { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border); }
.source-details summary { display: flex; align-items: center; gap: 7px; color: var(--primary-dark); cursor: pointer; font-size: 12px; font-weight: 750; list-style: none; }
.source-details summary::-webkit-details-marker { display: none; }
.source-details summary small { color: var(--muted); font-size: 11px; font-weight: 600; }
.source-details summary::after { margin-left: auto; color: var(--primary); content: '展开'; font-size: 11px; }
.source-details[open] summary::after { content: '收起'; }
.source-list { display: grid; gap: 7px; margin-top: 10px; }
.source-list a { display: grid; gap: 3px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; color: var(--ink); background: white; }
.source-list a:hover { background: var(--primary-soft); }
.source-list span { font-size: 12px; font-weight: 700; }
.source-list small { overflow: hidden; color: var(--muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.run-details { margin-top: 13px; padding-top: 11px; border-top: 1px solid var(--border); }
.run-details summary { color: var(--primary-dark); cursor: pointer; font-size: 12px; font-weight: 750; }
.run-meta { margin: 9px 0; color: var(--muted); font-size: 11px; }
.tool-list { display: grid; gap: 7px; margin: 0 0 10px; padding: 0; list-style: none; }
.tool-list li { padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface-soft); }
.tool-list li > div { display: flex; justify-content: space-between; gap: 10px; }
.tool-list span { color: var(--muted); font-size: 11px; }
.tool-list code { display: block; margin-top: 6px; overflow-wrap: anywhere; color: var(--muted-strong); font-size: 11px; }
.tool-list p { margin: 6px 0 0; color: var(--danger); font-size: 12px; }
.tool-list .tool-completed { border-left: 3px solid var(--success); }
.tool-list .tool-failed,
.tool-list .tool-denied { border-left: 3px solid var(--danger); }
.proposal-card { margin-top: 13px; padding: 13px; border: 1px solid #e3d3ac; border-radius: 7px; background: #fbf7ed; }
.proposal-card > div:first-child { display: flex; justify-content: space-between; gap: 12px; }
.proposal-card span { font-size: 11px; font-weight: 700; }
.proposal-card p { margin: 8px 0; color: var(--ink); }
.proposal-actions { display: flex; gap: 8px; }
.proposal-actions .button { min-height: 36px; }
.proposal-executed { color: var(--success); }
.proposal-rejected,
.proposal-failed { color: var(--danger); }
.composer { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; padding: 16px 20px; border-top: 1px solid var(--border); background: white; }
.composer textarea { width: 100%; padding: 12px 14px; border: 1px solid var(--border); border-radius: 12px; outline: none; resize: none; }
.composer textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 2px var(--primary-soft); }
.agent-error { margin: 0; padding: 10px 20px; color: var(--danger); background: var(--danger-soft); }
.chat-empty { align-self: center; }
.chat-empty p { margin-bottom: 0; }
@media (max-width: 900px) {
  .agent-layout { grid-template-columns: 1fr; }
  .session-sidebar { min-height: auto; }
  .chat-panel { min-height: 680px; }
}
@media (max-width: 620px) {
  .message-bubble { width: 94%; }
  .composer { grid-template-columns: 1fr; }
  .chat-header { align-items: flex-start; }
}
</style>
