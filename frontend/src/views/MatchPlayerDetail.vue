<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import {
  createPlayerHighlight,
  getClipExportContentUrl,
  listMatchClipExports,
  type ClipExportRecord,
  type ClipExportSegmentRecord,
} from '@/services/clipExports'
import {
  eventTypeLabels,
  listMatchEvents,
  type MatchEventRecord,
} from '@/services/events'
import {
  getMatchPlayerStats,
  getPlayerMetricEvents,
  listPlayerAssignmentAudits,
  reassignEventPlayers,
  type MatchPlayerStatsRecord,
  type PlayerAssignmentAuditRecord,
  type PlayerMatchStatsRecord,
  type PlayerStatsMetric,
} from '@/services/playerStats'
import { listPlayers, type PlayerRecord } from '@/services/players'
import { formatBytes, formatDuration } from '@/services/videos'
import { useAuthStore } from '@/stores/auth'

const metricLabels: Record<PlayerStatsMetric, string> = {
  goals: '进球',
  shots: '总射门',
  saves: '扑救',
  turnovers: '失误',
  fast_breaks: '快攻',
}
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const matchId = computed(() => Number(route.params.matchId))
const playerId = computed(() => Number(route.params.playerId))
const stats = ref<MatchPlayerStatsRecord | null>(null)
const players = ref<PlayerRecord[]>([])
const allEvents = ref<MatchEventRecord[]>([])
const metricEvents = ref<MatchEventRecord[]>([])
const audits = ref<PlayerAssignmentAuditRecord[]>([])
const exports = ref<ClipExportRecord[]>([])
const selectedMetric = ref<PlayerStatsMetric>('goals')
const activeEvent = ref<MatchEventRecord | null>(null)
const activeSegment = ref<ClipExportSegmentRecord | null>(null)
const videoPlayer = ref<HTMLVideoElement | null>(null)
const selectedCorrectionEventIds = ref<number[]>([])
const correctionPlayerId = ref<number | null>(null)
const loading = ref(true)
const metricLoading = ref(false)
const correctionSaving = ref(false)
const highlightCreating = ref(false)
const error = ref('')
const message = ref('')
const developmentNotice = ref('')
let exportPollTimer: number | undefined
let noticeTimer: number | undefined

const player = computed<PlayerMatchStatsRecord | null>(
  () => stats.value?.players.find((row) => row.player_id === playerId.value) ?? null,
)
const participantPlayers = computed(() => {
  if (!stats.value) return []
  const teamIds = new Set([stats.value.home_team_id, stats.value.away_team_id])
  return players.value.filter((item) => teamIds.has(item.team_id))
})
const playerHighlights = computed(() =>
  exports.value.filter(
    (item) =>
      item.export_type === 'player_highlight' &&
      item.player_id === playerId.value &&
      item.event_types.length === 1 &&
      item.event_types[0] === 'goal',
  ),
)
const activeHighlight = computed(
  () => playerHighlights.value.find((item) => item.status === 'completed') ?? null,
)
const relevantAudits = computed(() =>
  audits.value.filter(
    (audit) =>
      audit.old_player_id === playerId.value || audit.new_player_id === playerId.value,
  ),
)
const metricCards = computed(() => {
  const row = player.value
  return row
    ? [
        { metric: 'goals' as const, label: '进球', value: String(row.goals) },
        { metric: 'shots' as const, label: '总射门', value: String(row.shots) },
        {
          metric: 'shots' as const,
          label: '命中率',
          value:
            row.shooting_percentage === null
              ? '暂无数据'
              : `${row.shooting_percentage.toFixed(1)}%`,
        },
        { metric: 'saves' as const, label: '扑救', value: String(row.saves) },
        { metric: 'turnovers' as const, label: '失误', value: String(row.turnovers) },
        { metric: 'fast_breaks' as const, label: '快攻', value: String(row.fast_breaks) },
      ]
    : []
})

const formatEventTime = (seconds: number) => {
  const rounded = Math.max(0, Math.floor(seconds))
  const hours = Math.floor(rounded / 3600)
  const minutes = Math.floor((rounded % 3600) / 60)
  const remaining = rounded % 60
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remaining).padStart(2, '0')}`
    : `${minutes}:${String(remaining).padStart(2, '0')}`
}

const loadMetricEvents = async () => {
  metricLoading.value = true
  activeEvent.value = null
  try {
    metricEvents.value = await getPlayerMetricEvents(
      matchId.value,
      playerId.value,
      selectedMetric.value,
    )
  } finally {
    metricLoading.value = false
  }
}

const scheduleExportPoll = () => {
  if (exportPollTimer) window.clearTimeout(exportPollTimer)
  if (!playerHighlights.value.some((item) => ['queued', 'processing'].includes(item.status))) return
  exportPollTimer = window.setTimeout(async () => {
    exports.value = await listMatchClipExports(matchId.value)
    scheduleExportPoll()
  }, 2000)
}

const load = async () => {
  try {
    const [statsData, playerRows, eventRows, exportRows] = await Promise.all([
      getMatchPlayerStats(matchId.value),
      listPlayers(),
      listMatchEvents(matchId.value),
      listMatchClipExports(matchId.value),
    ])
    stats.value = statsData
    players.value = playerRows
    allEvents.value = eventRows
    exports.value = exportRows
    if (authStore.hasPermission('manage_competition_data')) {
      audits.value = await listPlayerAssignmentAudits(matchId.value)
    }
    await loadMetricEvents()
    scheduleExportPoll()
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : '球员比赛分析加载失败。'
  } finally {
    loading.value = false
  }
}

const showDevelopmentNotice = (label: string) => {
  developmentNotice.value = `${label}数据正在开发中，当前版本暂时只支持进球事件。`
  if (noticeTimer) window.clearTimeout(noticeTimer)
  noticeTimer = window.setTimeout(() => {
    developmentNotice.value = ''
  }, 3600)
}

const selectMetric = async (metric: PlayerStatsMetric, label: string) => {
  if (metric !== 'goals') {
    showDevelopmentNotice(label)
    return
  }
  selectedMetric.value = metric
  await router.replace({ query: { ...route.query, metric } })
  await loadMetricEvents()
}

const startActiveSegment = async () => {
  if (!videoPlayer.value || !activeSegment.value) return
  videoPlayer.value.currentTime = activeSegment.value.highlight_start_seconds
  try {
    await videoPlayer.value.play()
  } catch {
    // 浏览器可能阻止自动播放；片段定位仍然有效。
  }
}

const playEvent = async (event: MatchEventRecord) => {
  const segment = activeHighlight.value?.segments.find((item) => item.event_id === event.id)
  if (!activeHighlight.value || !segment) {
    developmentNotice.value = '该进球暂时没有可播放的集锦片段，请先生成最新的个人进球集锦。'
    return
  }
  activeEvent.value = event
  activeSegment.value = segment
  await nextTick()
  if (!videoPlayer.value) return
  if (videoPlayer.value.readyState === 0) {
    videoPlayer.value.addEventListener('loadedmetadata', () => void startActiveSegment(), {
      once: true,
    })
    videoPlayer.value.load()
    return
  }
  await startActiveSegment()
}

const playFullHighlight = async () => {
  activeEvent.value = null
  activeSegment.value = null
  await nextTick()
  if (!videoPlayer.value) return
  videoPlayer.value.currentTime = 0
  try {
    await videoPlayer.value.play()
  } catch {
    // 浏览器可能阻止自动播放；用户仍可使用原生播放按钮。
  }
}

const stopAtSegmentEnd = () => {
  if (!videoPlayer.value || !activeSegment.value) return
  const segmentEnd =
    activeSegment.value.highlight_start_seconds + activeSegment.value.duration_seconds
  if (videoPlayer.value.currentTime >= segmentEnd - 0.08) {
    videoPlayer.value.pause()
    videoPlayer.value.currentTime = segmentEnd
  }
}

const toggleCorrectionEvent = (eventId: number) => {
  selectedCorrectionEventIds.value = selectedCorrectionEventIds.value.includes(eventId)
    ? selectedCorrectionEventIds.value.filter((id) => id !== eventId)
    : [...selectedCorrectionEventIds.value, eventId]
}

const saveCorrections = async () => {
  if (!correctionPlayerId.value || selectedCorrectionEventIds.value.length === 0) return
  const target = participantPlayers.value.find((item) => item.id === correctionPlayerId.value)
  if (!target) return
  const count = selectedCorrectionEventIds.value.length
  if (!window.confirm(`将 ${count} 个事件统一关联到 ${target.name}，确认继续吗？`)) return
  correctionSaving.value = true
  error.value = ''
  try {
    const result = await reassignEventPlayers(
      matchId.value,
      selectedCorrectionEventIds.value,
      target.id,
    )
    message.value = `已检查 ${result.requested_count} 个事件，更新 ${result.affected_count} 个球员关联。`
    selectedCorrectionEventIds.value = []
    const [statsData, eventRows] = await Promise.all([
      getMatchPlayerStats(matchId.value),
      listMatchEvents(matchId.value),
    ])
    stats.value = statsData
    allEvents.value = eventRows
    if (authStore.hasPermission('manage_competition_data')) {
      audits.value = await listPlayerAssignmentAudits(matchId.value)
    }
    await loadMetricEvents()
  } catch (saveError) {
    error.value = saveError instanceof Error ? saveError.message : '球员关联更新失败。'
  } finally {
    correctionSaving.value = false
  }
}

const createHighlight = async () => {
  highlightCreating.value = true
  error.value = ''
  try {
    const task = await createPlayerHighlight(
      matchId.value,
      playerId.value,
      ['goal'],
    )
    exports.value = [task, ...exports.value]
    message.value = `个人集锦任务已创建，将合并 ${task.event_ids.length} 个事件片段。`
    scheduleExportPoll()
  } catch (createError) {
    error.value = createError instanceof Error ? createError.message : '个人集锦创建失败。'
  } finally {
    highlightCreating.value = false
  }
}

onMounted(load)
onUnmounted(() => {
  if (exportPollTimer) window.clearTimeout(exportPollTimer)
  if (noticeTimer) window.clearTimeout(noticeTimer)
})
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" :to="{ name: 'player-stats', params: { matchId } }">
        ← 返回球员单场统计
      </RouterLink>
      <div v-if="loading" class="detail-card empty-state">正在加载球员事件…</div>
      <div v-else-if="!player" class="detail-card empty-state">
        {{ error || '这名球员不属于当前比赛。' }}
      </div>

      <template v-else>
        <section class="player-hero">
          <div class="jersey-number">{{ player.player_number }}</div>
          <div>
            <p class="eyebrow">Player Match Analysis</p>
            <h1>{{ player.player_name }}</h1>
            <p>{{ player.team_name }} · {{ player.position || '位置待完善' }}</p>
          </div>
          <a class="highlight-shortcut" href="#player-highlight">生成个人集锦 ↓</a>
        </section>

        <section class="metric-grid" aria-label="球员统计指标">
          <button
            v-for="card in metricCards"
            :key="`${card.label}-${card.metric}`"
            class="metric-card"
            :class="{
              active: selectedMetric === card.metric && card.metric === 'goals',
              unavailable: card.metric !== 'goals',
            }"
            @click="selectMetric(card.metric, card.label)"
          >
            <span>{{ card.label }}</span><strong>{{ card.value }}</strong>
            <small v-if="card.metric !== 'goals'">后续开放</small>
          </button>
        </section>

        <Transition name="notice">
          <div v-if="developmentNotice" class="development-notice" role="status">
            <strong>功能提示</strong>
            <span>{{ developmentNotice }}</span>
            <button type="button" aria-label="关闭通知" @click="developmentNotice = ''">×</button>
          </div>
        </Transition>

        <p v-if="message" class="success page-message">{{ message }}</p>
        <p v-if="error" class="error page-message">{{ error }}</p>

        <section class="review-layout">
          <div class="detail-card video-review">
            <div class="section-heading">
              <div><p class="eyebrow">Video Review</p><h2>个人进球集锦</h2></div>
              <div class="video-heading-actions">
                <span class="meta-chip">{{ metricEvents.length }} 个进球片段</span>
                <button
                  v-if="activeHighlight"
                  class="button button-secondary"
                  type="button"
                  @click="playFullHighlight"
                >
                  播放完整集锦
                </button>
              </div>
            </div>
            <video
              v-if="activeHighlight"
              ref="videoPlayer"
              :key="activeHighlight.id"
              class="review-video"
              :src="getClipExportContentUrl(activeHighlight.id)"
              controls
              preload="metadata"
              @timeupdate="stopAtSegmentEnd"
            />
            <div v-else class="video-placeholder">
              <div>
                <strong>还没有可播放的个人进球集锦</strong>
                <p>请在下方生成集锦；生成完成后，这里只播放集锦内容，不会加载整场录像。</p>
              </div>
            </div>
            <p v-if="activeEvent" class="segment-caption">
              正在播放 {{ formatEventTime(activeEvent.timestamp_seconds) }} 的进球片段，片段结束后会自动暂停。
            </p>
          </div>

          <div class="detail-card event-list-card">
            <h2>{{ metricLabels[selectedMetric] }}时间点</h2>
            <p v-if="metricLoading" class="empty-state">正在读取事件…</p>
            <button
              v-for="event in metricEvents"
              v-else
              :key="event.id"
              class="event-row"
              :class="{ active: activeEvent?.id === event.id }"
              @click="playEvent(event)"
            >
              <span><strong>{{ formatEventTime(event.timestamp_seconds) }}</strong><small>{{ eventTypeLabels[event.event_type] }}</small></span>
              <span>播放片段 →</span>
            </button>
            <p v-if="!metricLoading && metricEvents.length === 0" class="empty-state">
              该指标没有已确认事件，不会显示虚构内容。
            </p>
          </div>
        </section>

        <section id="player-highlight" class="detail-card highlight-section">
          <div class="section-heading">
            <div><p class="eyebrow">Personal Highlight</p><h2>生成个人进球集锦</h2></div>
          </div>
          <p class="page-description">系统会按比赛时间合并这名球员所有已确认的进球片段。当前版本暂不生成射门、扑救、失误或快攻集锦。</p>
          <button
            class="button button-primary"
            :disabled="highlightCreating"
            @click="createHighlight"
          >
            {{ highlightCreating ? '正在创建…' : '生成个人集锦' }}
          </button>

          <div v-if="playerHighlights.length" class="highlight-list">
            <article v-for="task in playerHighlights" :key="task.id" class="highlight-row">
              <div>
                <strong>{{ task.filename }}</strong>
                <p>{{ task.event_ids.length }} 个事件 · {{ task.event_types.map((type) => eventTypeLabels[type]).join('、') }}</p>
                <small v-if="task.status === 'completed'">{{ formatDuration(task.duration_seconds) }} · {{ formatBytes(task.size_bytes ?? 0) }}</small>
                <small v-else-if="task.status === 'failed'" class="error">{{ task.failure_reason }}</small>
                <small v-else>正在{{ task.status === 'queued' ? '排队' : '生成' }}…</small>
              </div>
              <div v-if="task.status === 'completed'" class="highlight-actions">
                <a class="button button-secondary" :href="getClipExportContentUrl(task.id)" target="_blank">预览</a>
                <a class="button button-primary" :href="getClipExportContentUrl(task.id, true)">下载 MP4</a>
              </div>
            </article>
          </div>
        </section>

        <section
          v-if="authStore.hasPermission('upload_and_annotate_video')"
          class="detail-card correction-section"
        >
          <div class="section-heading">
            <div><p class="eyebrow">Manual Correction</p><h2>批量纠正事件球员</h2></div>
            <span class="meta-chip">已选择 {{ selectedCorrectionEventIds.length }} 个事件</span>
          </div>
          <p class="page-description">这里包含本场全部有效记录，包括尚未关联球员的 AI 草稿；草稿只有确认后才会进入正式统计。</p>
          <div class="correction-toolbar">
            <select v-model.number="correctionPlayerId">
              <option :value="null">选择正确球员</option>
              <option v-for="item in participantPlayers" :key="item.id" :value="item.id">
                {{ item.number }}号 {{ item.name }}（{{ item.team_id === stats?.home_team_id ? stats?.home_team_name : stats?.away_team_name }}）
              </option>
            </select>
            <strong>本次操作将影响 {{ selectedCorrectionEventIds.length }} 个事件</strong>
            <button
              class="button button-primary"
              :disabled="!correctionPlayerId || selectedCorrectionEventIds.length === 0 || correctionSaving"
              @click="saveCorrections"
            >
              {{ correctionSaving ? '正在保存…' : '确认批量更新' }}
            </button>
          </div>
          <div class="correction-list">
            <label v-for="event in allEvents" :key="event.id" class="correction-row">
              <input
                type="checkbox"
                :checked="selectedCorrectionEventIds.includes(event.id)"
                @change="toggleCorrectionEvent(event.id)"
              />
              <span>{{ formatEventTime(event.timestamp_seconds) }}</span>
              <strong>{{ eventTypeLabels[event.event_type] }}</strong>
              <span>{{ participantPlayers.find((item) => item.id === event.player_id)?.name ?? '未关联球员' }}</span>
              <span :class="event.status === 'verified' ? 'status-ready' : 'status-neutral'" class="status-badge">
                {{ event.status === 'verified' ? '已确认' : 'AI 草稿' }}
              </span>
            </label>
          </div>
        </section>

        <section
          v-if="authStore.hasPermission('manage_competition_data')"
          class="detail-card audit-section"
        >
          <div class="section-heading"><div><p class="eyebrow">Audit Trail</p><h2>球员关联审计</h2></div></div>
          <div v-if="relevantAudits.length" class="audit-list">
            <div v-for="audit in relevantAudits" :key="audit.id" class="audit-row">
              <strong>事件 #{{ audit.event_id }}</strong>
              <span>{{ audit.old_player_name ?? '未关联' }} → {{ audit.new_player_name }}</span>
              <span>{{ audit.changed_by_user_name }}（#{{ audit.changed_by_user_id }}）</span>
              <time>{{ new Date(audit.changed_at).toLocaleString('zh-CN') }}</time>
            </div>
          </div>
          <p v-else class="empty-state">暂时没有球员关联修改记录。</p>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.player-hero { display: flex; align-items: center; gap: 22px; padding: 26px 30px; border: 1px solid var(--border); border-radius: 10px; color: var(--ink); background: white; }
.player-hero h1 { margin: 0; font-size: 34px; }
.player-hero p:last-child { margin: 7px 0 0; color: var(--muted-strong); }
.highlight-shortcut { margin-left: auto; padding: 10px 14px; border: 1px solid var(--border); border-radius: 7px; color: var(--primary-dark); background: white; font-size: 13px; font-weight: 700; text-decoration: none; }
.highlight-shortcut:hover { background: var(--surface-soft); }
.jersey-number { display: grid; width: 68px; height: 68px; place-items: center; border: 1px solid var(--border-strong); border-radius: 50%; font-size: 30px; font-weight: 750; }
.metric-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }
.metric-card { display: grid; gap: 7px; padding: 16px; border: 1px solid var(--border); border-radius: 7px; color: var(--muted-strong); background: white; cursor: pointer; text-align: left; }
.metric-card strong { color: var(--ink); font-size: 24px; }
.metric-card.active { border-color: var(--primary); background: var(--primary-soft); }
.metric-card small { color: var(--muted); font-size: 11px; font-weight: 650; }
.metric-card.unavailable { position: relative; }
.metric-card.unavailable:hover { border-color: #b9c7da; background: var(--surface-soft); }
.page-message { margin: 16px 0 0; }
.development-notice { position: fixed; z-index: 40; top: 88px; right: 24px; display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 10px; max-width: 520px; padding: 14px 16px; border: 1px solid #f4cf7a; border-radius: 12px; color: #754c00; background: #fff8e8; box-shadow: var(--shadow-card); }
.development-notice strong { white-space: nowrap; }
.development-notice button { border: 0; color: #8a6420; background: transparent; cursor: pointer; font-size: 20px; line-height: 1; }
.notice-enter-active, .notice-leave-active { transition: opacity .18s ease, transform .18s ease; }
.notice-enter-from, .notice-leave-to { opacity: 0; transform: translateY(-8px); }
.review-layout { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(300px, .55fr); gap: 18px; margin-top: 24px; }
.section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.section-heading h2, .event-list-card h2 { margin: 0 0 16px; font-size: 20px; }
.video-heading-actions { display: flex; align-items: center; gap: 8px; }
.video-heading-actions .button { min-height: 34px; padding: 7px 11px; }
.review-video { width: 100%; margin-top: 8px; border-radius: 7px; background: #080b14; }
.video-placeholder { display: grid; min-height: 330px; margin-top: 8px; place-items: center; border-radius: 7px; color: var(--muted); background: var(--surface-soft); text-align: center; }
.video-placeholder strong { color: var(--ink); }
.video-placeholder p { max-width: 520px; margin: 8px 20px 0; }
.segment-caption { margin: 10px 0 0; color: var(--muted-strong); font-size: 13px; }
.event-list-card { max-height: 540px; overflow-y: auto; }
.event-row { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 12px; padding: 13px; border: 1px solid var(--border); border-radius: 11px; background: white; cursor: pointer; text-align: left; }
.event-row + .event-row { margin-top: 8px; }
.event-row span:first-child { display: grid; gap: 3px; }
.event-row small { color: var(--muted); }
.event-row.active { border-color: var(--primary); background: var(--primary-soft); }
.highlight-section, .correction-section, .audit-section { margin-top: 22px; }
.type-options { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; }
.type-options label { display: flex; align-items: center; gap: 7px; padding: 9px 12px; border: 1px solid var(--border); border-radius: 6px; }
.highlight-list { display: grid; gap: 10px; margin-top: 20px; }
.highlight-row { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 15px; border: 1px solid var(--border); border-radius: 12px; }
.highlight-row p { margin: 5px 0; color: var(--muted-strong); }
.highlight-actions { display: flex; gap: 8px; }
.correction-toolbar { display: grid; grid-template-columns: minmax(220px, 1fr) auto auto; align-items: center; gap: 14px; margin: 18px 0; }
.correction-toolbar select { height: 42px; padding: 0 11px; border: 1px solid var(--border); border-radius: 10px; background: white; }
.correction-toolbar strong { color: var(--warning); font-size: 13px; }
.correction-list { max-height: 390px; overflow-y: auto; border: 1px solid var(--border); border-radius: 12px; }
.correction-row { display: grid; grid-template-columns: auto 80px 110px 1fr auto; align-items: center; gap: 12px; padding: 11px 14px; }
.correction-row + .correction-row { border-top: 1px solid var(--border); }
.audit-list { display: grid; gap: 8px; }
.audit-row { display: grid; grid-template-columns: 100px 1fr 140px 190px; gap: 12px; padding: 12px; border-radius: 10px; background: var(--surface-soft); }

@media (max-width: 980px) {
  .player-hero { align-items: flex-start; flex-direction: column; }
  .highlight-shortcut { margin-left: 0; }
  .metric-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .review-layout { grid-template-columns: 1fr; }
  .correction-toolbar, .audit-row { grid-template-columns: 1fr; }
}
@media (max-width: 620px) {
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .highlight-row { align-items: flex-start; flex-direction: column; }
  .correction-row { grid-template-columns: auto 64px 1fr; }
  .correction-row span:nth-last-child(-n+2) { grid-column: 2 / -1; }
  .development-notice { top: 72px; right: 12px; left: 12px; }
  .video-heading-actions { align-items: flex-end; flex-direction: column; }
}
</style>
