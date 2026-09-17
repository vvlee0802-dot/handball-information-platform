<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { listCompetitions, type CompetitionRecord } from '@/services/competitions'
import {
  createMatchEvent,
  deleteMatchEvent,
  eventTypeLabels,
  listMatchEvents,
  updateMatchEvent,
  validateEventTimestamp,
  verifyMatchEvent,
  type EventType,
  type MatchEventInput,
  type MatchEventRecord,
} from '@/services/events'
import {
  deleteMatch,
  getMatch,
  matchStatusLabels,
  updateMatch,
  type MatchInput,
  type MatchRecord,
} from '@/services/matches'
import { listTeams, type TeamRecord } from '@/services/teams'
import { listPlayers, type PlayerRecord } from '@/services/players'
import { listVenues, type VenueRecord } from '@/services/venues'
import {
  deleteVideo,
  formatBytes,
  formatDuration,
  getVideoContentUrl,
  getVideoUploadPolicy,
  listMatchVideos,
  retryVideoProcessing,
  readVideoDuration,
  uploadMatchVideoResumable,
  validateVideoFile,
  type VideoRecord,
  type VideoProcessingStatus,
  type VideoType,
  type VideoUploadPolicy,
} from '@/services/videos'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const match = ref<MatchRecord | null>(null)
const competitions = ref<CompetitionRecord[]>([])
const teams = ref<TeamRecord[]>([])
const venues = ref<VenueRecord[]>([])
const players = ref<PlayerRecord[]>([])
const loading = ref(true),
  editing = ref(false),
  saving = ref(false),
  deletingMatch = ref(false)
const error = ref(''),
  message = ref(''),
  deleteError = ref('')
const videos = ref<VideoRecord[]>([])
const uploadPolicy = ref<VideoUploadPolicy | null>(null)
const selectedVideo = ref<File | null>(null)
const selectedVideoDuration = ref<number | null>(null)
const selectedVideoType = ref<VideoType>('original')
const videoInput = ref<HTMLInputElement | null>(null)
const videoError = ref('')
const videoMessage = ref('')
const uploadProgress = ref(0)
const uploading = ref(false)
const retryingVideoId = ref<number | null>(null)
const deletingVideoId = ref<number | null>(null)
const events = ref<MatchEventRecord[]>([])
const selectedPlaybackVideoId = ref<number | null>(null)
const videoPlayer = ref<HTMLVideoElement | null>(null)
const currentVideoTime = ref(0)
const eventSaving = ref(false)
const editingEventId = ref<number | null>(null)
const deletingEventId = ref<number | null>(null)
const verifyingEventId = ref<number | null>(null)
const pendingSeekTime = ref<number | null>(null)
const eventError = ref('')
const eventMessage = ref('')
let videoPollTimer: ReturnType<typeof setTimeout> | null = null
let activeUploadController: AbortController | null = null
const form = reactive<MatchInput>({
  competition_id: 0,
  home_team_id: 0,
  away_team_id: 0,
  venue_id: 0,
  match_date: '',
  start_time: '',
  stage: '',
  status: 'scheduled',
  home_score: null,
  away_score: null,
})
const eventForm = reactive<MatchEventInput>({
  video_id: 0,
  event_type: 'goal',
  timestamp_seconds: 0,
  team_id: null,
  player_id: null,
  note: null,
})
const eventFilters = reactive<{
  event_type: EventType | ''
  team_id: number | null
  player_id: number | null
  status: 'draft' | 'verified' | ''
}>({
  event_type: '',
  team_id: null,
  player_id: null,
  status: '',
})
const competition = computed(() =>
  competitions.value.find((x) => x.id === match.value?.competition_id),
)
const home = computed(() => teams.value.find((x) => x.id === match.value?.home_team_id))
const away = computed(() => teams.value.find((x) => x.id === match.value?.away_team_id))
const venue = computed(() => venues.value.find((x) => x.id === match.value?.venue_id))
const playbackVideo = computed(() =>
  videos.value.find((video) => video.id === selectedPlaybackVideoId.value),
)
const participantPlayers = computed(() => {
  if (!match.value) return []
  const participantTeamIds = new Set([match.value.home_team_id, match.value.away_team_id])
  return players.value.filter((player) => participantTeamIds.has(player.team_id))
})
const selectablePlayers = computed(() =>
  eventForm.team_id === null
    ? participantPlayers.value
    : participantPlayers.value.filter((player) => player.team_id === eventForm.team_id),
)
const filterPlayers = computed(() =>
  eventFilters.team_id === null
    ? participantPlayers.value
    : participantPlayers.value.filter((player) => player.team_id === eventFilters.team_id),
)
const eventStatistics = computed(() => ({
  total: events.value.length,
  verified: events.value.filter((event) => event.status === 'verified').length,
  draft: events.value.filter((event) => event.status === 'draft').length,
}))
const scoresEnabled = computed(() => form.status === 'live' || form.status === 'completed')
const processingLabels: Record<VideoProcessingStatus, string> = {
  queued: '等待处理',
  processing: '处理中',
  completed: '处理完成',
  failed: '处理失败',
}
const processingClasses: Record<VideoProcessingStatus, string> = {
  queued: 'status-neutral',
  processing: 'status-processing',
  completed: 'status-ready',
  failed: 'status-failed',
}
const videoTypeLabels: Record<VideoType, string> = {
  original: '原始录像',
  supplementary: '补充机位',
  processed: '处理结果',
}
const formatUploadTime = (value: string) => new Date(value).toLocaleString('zh-CN')

const fill = (record: MatchRecord) =>
  Object.assign(form, { ...record, start_time: record.start_time.slice(0, 5) })
const load = async () => {
  try {
    const [record, cs, ts, vs, ps] = await Promise.all([
      getMatch(Number(route.params.matchId)),
      listCompetitions(),
      listTeams(),
      listVenues(),
      listPlayers(),
    ])
    match.value = record
    competitions.value = cs
    teams.value = ts
    venues.value = vs
    players.value = ps
    fill(record)
  } catch {
    match.value = null
  } finally {
    loading.value = false
  }
}
const startEdit = () => {
  if (match.value) {
    fill(match.value)
    error.value = ''
    message.value = ''
    editing.value = true
  }
}
const cancel = () => {
  if (match.value) fill(match.value)
  error.value = ''
  editing.value = false
}
watch(
  () => form.status,
  (status) => {
    if (status === 'scheduled' || status === 'cancelled') {
      form.home_score = null
      form.away_score = null
    }
  },
)
const save = async () => {
  if (!match.value) return
  error.value = ''
  saving.value = true
  try {
    const updated = await updateMatch(match.value.id, {
      ...form,
      start_time: form.start_time.length === 5 ? `${form.start_time}:00` : form.start_time,
    })
    match.value = updated
    fill(updated)
    editing.value = false
    message.value = '比赛信息已保存。'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

const removeMatch = async () => {
  if (!match.value) return
  const label = `${home.value?.name ?? '主队'} vs ${away.value?.name ?? '客队'}`
  if (!window.confirm(`确定删除比赛“${label}”吗？删除后无法恢复。`)) return
  deleteError.value = ''
  deletingMatch.value = true
  try {
    await deleteMatch(match.value.id)
    await router.push({ name: 'matches' })
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : '比赛删除失败'
  } finally {
    deletingMatch.value = false
  }
}

const loadVideos = async () => {
  if (!match.value || !authStore.hasPermission('view_authorized_video')) return
  try {
    videos.value = await listMatchVideos(match.value.id)
    if (
      selectedPlaybackVideoId.value !== null &&
      !videos.value.some((video) => video.id === selectedPlaybackVideoId.value)
    ) {
      selectedPlaybackVideoId.value = null
    }
  } catch (e) {
    videoError.value = e instanceof Error ? e.message : '视频记录加载失败'
  } finally {
    scheduleVideoPolling()
  }
}

const loadEvents = async () => {
  if (!match.value || !authStore.hasPermission('view_authorized_video')) return
  try {
    events.value = await listMatchEvents(match.value.id, {
      event_type: eventFilters.event_type || undefined,
      team_id: eventFilters.team_id ?? undefined,
      player_id: eventFilters.player_id ?? undefined,
      status: eventFilters.status || undefined,
    })
  } catch (e) {
    eventError.value = e instanceof Error ? e.message : '事件记录加载失败'
  }
}

const selectPlaybackVideo = (video: VideoRecord) => {
  editingEventId.value = null
  selectedPlaybackVideoId.value = video.id
  eventForm.video_id = video.id
  eventForm.timestamp_seconds = 0
  currentVideoTime.value = 0
  eventError.value = ''
  eventMessage.value = ''
}

const updateCurrentVideoTime = () => {
  currentVideoTime.value = videoPlayer.value?.currentTime ?? 0
  eventForm.timestamp_seconds = Number(currentVideoTime.value.toFixed(3))
}

const seekFromEventTimestamp = () => {
  if (!videoPlayer.value) return
  const duration = videoPlayer.value.duration
  const requestedTime = Math.max(0, Number(eventForm.timestamp_seconds) || 0)
  const safeTime = Number.isFinite(duration) ? Math.min(requestedTime, duration) : requestedTime
  videoPlayer.value.currentTime = safeTime
  currentVideoTime.value = safeTime
  eventForm.timestamp_seconds = Number(safeTime.toFixed(3))
}

const applyPendingSeek = () => {
  if (pendingSeekTime.value === null || !videoPlayer.value || videoPlayer.value.readyState === 0)
    return
  const validationError = validateEventTimestamp(
    pendingSeekTime.value,
    Number.isFinite(videoPlayer.value.duration) ? videoPlayer.value.duration : null,
  )
  if (validationError) {
    eventError.value = validationError
    pendingSeekTime.value = null
    return
  }
  eventForm.timestamp_seconds = pendingSeekTime.value
  seekFromEventTimestamp()
  pendingSeekTime.value = null
}

const handlePlayerSelection = () => {
  if (eventForm.player_id === null) return
  const player = participantPlayers.value.find((item) => item.id === eventForm.player_id)
  if (player) eventForm.team_id = player.team_id
}

watch(
  () => eventForm.team_id,
  (teamId) => {
    if (eventForm.player_id === null) return
    const player = participantPlayers.value.find((item) => item.id === eventForm.player_id)
    if (!player || (teamId !== null && player.team_id !== teamId)) eventForm.player_id = null
  },
)

watch(
  () => eventFilters.team_id,
  (teamId) => {
    if (eventFilters.player_id === null) return
    const player = participantPlayers.value.find((item) => item.id === eventFilters.player_id)
    if (!player || (teamId !== null && player.team_id !== teamId)) {
      eventFilters.player_id = null
    }
  },
)

const resetEventFilters = async () => {
  eventFilters.event_type = ''
  eventFilters.team_id = null
  eventFilters.player_id = null
  eventFilters.status = ''
  await loadEvents()
}

const showEventInPlayer = async (event: MatchEventRecord): Promise<boolean> => {
  const video = videos.value.find((item) => item.id === event.video_id)
  if (!video) {
    eventError.value = '该事件关联的视频当前不可用。'
    return false
  }
  const validationError = validateEventTimestamp(event.timestamp_seconds, video.duration_seconds)
  if (validationError) {
    eventError.value = validationError
    return false
  }
  selectedPlaybackVideoId.value = video.id
  editingEventId.value = null
  eventForm.video_id = video.id
  eventForm.timestamp_seconds = event.timestamp_seconds
  currentVideoTime.value = event.timestamp_seconds
  pendingSeekTime.value = event.timestamp_seconds
  eventError.value = ''
  eventMessage.value = ''
  await nextTick()
  applyPendingSeek()
  videoPlayer.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  return true
}

const jumpToEvent = async (event: MatchEventRecord) => {
  await showEventInPlayer(event)
}

const submitEvent = async () => {
  if (!match.value || !playbackVideo.value) return
  eventSaving.value = true
  eventError.value = ''
  eventMessage.value = ''
  try {
    const payload = {
      event_type: eventForm.event_type,
      timestamp_seconds: eventForm.timestamp_seconds,
      team_id: eventForm.team_id,
      player_id: eventForm.player_id,
      note: eventForm.note?.trim() || null,
    }
    if (editingEventId.value === null) {
      await createMatchEvent(match.value.id, {
        video_id: playbackVideo.value.id,
        ...payload,
      })
      eventMessage.value = `已在 ${formatDuration(eventForm.timestamp_seconds)} 保存人工事件。`
    } else {
      await updateMatchEvent(match.value.id, editingEventId.value, payload)
      eventMessage.value = `已更新 ${formatDuration(eventForm.timestamp_seconds)} 的事件，状态回到待确认。`
      editingEventId.value = null
    }
    eventForm.event_type = 'goal'
    eventForm.team_id = null
    eventForm.player_id = null
    eventForm.note = null
    await loadEvents()
  } catch (e) {
    eventError.value = e instanceof Error ? e.message : '事件保存失败'
  } finally {
    eventSaving.value = false
  }
}

const startEditEvent = async (event: MatchEventRecord) => {
  if (!(await showEventInPlayer(event))) return
  editingEventId.value = event.id
  eventForm.event_type = event.event_type
  eventForm.timestamp_seconds = event.timestamp_seconds
  eventForm.team_id = event.team_id
  eventForm.player_id = event.player_id
  eventForm.note = event.note
}

const cancelEventEdit = () => {
  editingEventId.value = null
  eventForm.event_type = 'goal'
  eventForm.timestamp_seconds = Number(currentVideoTime.value.toFixed(3))
  eventForm.team_id = null
  eventForm.player_id = null
  eventForm.note = null
  eventError.value = ''
  eventMessage.value = ''
}

const removeEvent = async (event: MatchEventRecord) => {
  if (!match.value) return
  if (!window.confirm(`确定删除 ${formatDuration(event.timestamp_seconds)} 的事件吗？`)) return
  deletingEventId.value = event.id
  eventError.value = ''
  try {
    await deleteMatchEvent(match.value.id, event.id)
    if (editingEventId.value === event.id) cancelEventEdit()
    eventMessage.value = '事件已删除，不再参与后续统计或导出。'
    await loadEvents()
  } catch (e) {
    eventError.value = e instanceof Error ? e.message : '事件删除失败'
  } finally {
    deletingEventId.value = null
  }
}

const confirmEvent = async (event: MatchEventRecord) => {
  if (!match.value) return
  verifyingEventId.value = event.id
  eventError.value = ''
  try {
    await verifyMatchEvent(match.value.id, event.id)
    eventMessage.value = `已确认 ${formatDuration(event.timestamp_seconds)} 的事件。`
    await loadEvents()
  } catch (e) {
    eventError.value = e instanceof Error ? e.message : '事件确认失败'
  } finally {
    verifyingEventId.value = null
  }
}

const scheduleVideoPolling = () => {
  if (videoPollTimer) clearTimeout(videoPollTimer)
  videoPollTimer = null
  const hasActiveTask = videos.value.some((video) =>
    ['queued', 'processing'].includes(video.processing_status),
  )
  if (hasActiveTask) {
    videoPollTimer = setTimeout(() => void loadVideos(), 1500)
  }
}

const loadUploadPolicy = async () => {
  if (!authStore.hasPermission('upload_and_annotate_video')) return
  try {
    uploadPolicy.value = await getVideoUploadPolicy()
  } catch (e) {
    videoError.value = e instanceof Error ? e.message : '上传规则加载失败'
  }
}

const chooseVideo = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null
  selectedVideo.value = file
  selectedVideoDuration.value = null
  videoError.value = ''
  videoMessage.value = ''
  if (file && uploadPolicy.value) {
    videoError.value = validateVideoFile(file, uploadPolicy.value) ?? ''
    if (!videoError.value) {
      const duration = await readVideoDuration(file)
      if (selectedVideo.value === file) selectedVideoDuration.value = duration
    }
  }
}

const submitVideo = async () => {
  if (!match.value || !selectedVideo.value || !uploadPolicy.value) return
  const validationError = validateVideoFile(selectedVideo.value, uploadPolicy.value)
  if (validationError) {
    videoError.value = validationError
    return
  }

  uploading.value = true
  activeUploadController = new AbortController()
  uploadProgress.value = 0
  videoError.value = ''
  videoMessage.value = ''
  try {
    await uploadMatchVideoResumable(match.value.id, selectedVideo.value, {
      signal: activeUploadController.signal,
      videoType: selectedVideoType.value,
      durationSeconds: selectedVideoDuration.value,
      onProgress: (percent) => {
        uploadProgress.value = percent
      },
      onResume: (uploadedParts, percent) => {
        videoMessage.value = `检测到 ${uploadedParts} 个已上传分片，从 ${percent}% 继续。`
      },
    })
    videoMessage.value = '录像上传成功，已经与本场比赛关联。'
    selectedVideo.value = null
    selectedVideoDuration.value = null
    selectedVideoType.value = 'original'
    if (videoInput.value) videoInput.value.value = ''
    await loadVideos()
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      videoMessage.value = '上传已取消，服务器临时分片已清理。'
    } else {
      const reason = e instanceof Error ? e.message : '视频上传失败'
      videoError.value = `${reason} 重新选择同一个文件即可从已完成的分片继续。`
    }
  } finally {
    uploading.value = false
    activeUploadController = null
  }
}

const cancelUpload = () => {
  activeUploadController?.abort()
}

const retryProcessing = async (video: VideoRecord) => {
  retryingVideoId.value = video.id
  videoError.value = ''
  videoMessage.value = ''
  try {
    await retryVideoProcessing(video.id)
    videoMessage.value = `已重新提交 ${video.original_filename} 的处理任务。`
    await loadVideos()
  } catch (e) {
    videoError.value = e instanceof Error ? e.message : '重新处理失败'
  } finally {
    retryingVideoId.value = null
  }
}

const removeVideo = async (video: VideoRecord) => {
  if (!window.confirm(`确定删除视频“${video.original_filename}”吗？服务器文件也会被删除。`)) return
  deletingVideoId.value = video.id
  videoError.value = ''
  videoMessage.value = ''
  try {
    await deleteVideo(video.id)
    videoMessage.value = `已删除 ${video.original_filename}。`
    await loadVideos()
  } catch (e) {
    videoError.value = e instanceof Error ? e.message : '视频删除失败'
  } finally {
    deletingVideoId.value = null
  }
}

watch(
  [
    () => authStore.initialized,
    () => authStore.user?.permissions.join(','),
    () => match.value?.id,
  ],
  ([initialized, , matchId]) => {
    if (!initialized || !matchId) return
    void loadVideos()
    void loadEvents()
    void loadUploadPolicy()
  },
  { immediate: true },
)
onMounted(load)
onUnmounted(() => {
  if (videoPollTimer) clearTimeout(videoPollTimer)
  activeUploadController?.abort()
})
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/matches">← 返回比赛列表</RouterLink>
      <div v-if="loading" class="detail-card empty-state">正在加载比赛…</div>
      <NotFoundPanel v-else-if="!match" entity="比赛" />
      <section v-else class="detail-card">
        <div class="detail-header">
          <div>
            <p class="eyebrow">{{ competition?.name }}</p>
            <h1 class="detail-title">{{ home?.short_name }} vs {{ away?.short_name }}</h1>
            <div class="detail-meta">
              <span class="meta-chip">{{ match.stage }}</span
              ><span class="meta-chip">{{ matchStatusLabels[match.status] }}</span
              ><span class="meta-chip"
                >{{ match.match_date }} {{ match.start_time.slice(0, 5) }}</span
              >
            </div>
          </div>
          <div class="detail-actions">
            <div class="score">{{ match.home_score ?? '—' }} : {{ match.away_score ?? '—' }}</div>
            <button
              v-if="!editing && authStore.hasPermission('manage_competition_data')"
              class="button button-secondary"
              @click="startEdit"
            >
              编辑比赛
            </button>
            <button
              v-if="!editing && authStore.hasPermission('manage_competition_data')"
              class="button button-danger"
              type="button"
              :disabled="deletingMatch"
              @click="removeMatch"
            >
              {{ deletingMatch ? '删除中…' : '删除比赛' }}
            </button>
          </div>
        </div>

        <p v-if="!editing && deleteError" class="error">删除失败：{{ deleteError }}</p>

        <form v-if="editing" class="edit-form" @submit.prevent="save">
          <div class="filter-grid">
            <div class="field">
              <label>赛事</label
              ><select v-model.number="form.competition_id">
                <option v-for="x in competitions" :key="x.id" :value="x.id">{{ x.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>主队</label
              ><select v-model.number="form.home_team_id">
                <option v-for="x in teams" :key="x.id" :value="x.id">{{ x.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>客队</label
              ><select v-model.number="form.away_team_id">
                <option v-for="x in teams" :key="x.id" :value="x.id">{{ x.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>场馆</label
              ><select v-model.number="form.venue_id">
                <option v-for="x in venues" :key="x.id" :value="x.id">{{ x.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>日期</label><input v-model="form.match_date" type="date" required />
            </div>
            <div class="field">
              <label>时间</label><input v-model="form.start_time" type="time" required />
            </div>
            <div class="field">
              <label>阶段</label><input v-model="form.stage" required maxlength="80" />
            </div>
            <div class="field">
              <label>状态</label
              ><select v-model="form.status">
                <option value="scheduled">未开始</option>
                <option value="live">进行中</option>
                <option value="completed">已结束</option>
                <option value="cancelled">已取消</option>
              </select>
            </div>
            <div class="field">
              <label>主队比分</label
              ><input
                v-model.number="form.home_score"
                type="number"
                min="0"
                :required="form.status === 'completed'"
                :disabled="!scoresEnabled"
              />
            </div>
            <div class="field">
              <label>客队比分</label
              ><input
                v-model.number="form.away_score"
                type="number"
                min="0"
                :required="form.status === 'completed'"
                :disabled="!scoresEnabled"
              />
            </div>
          </div>
          <p v-if="error" class="error">保存失败：{{ error }}</p>
          <div class="filter-actions">
            <button
              class="button button-secondary"
              type="button"
              :disabled="saving"
              @click="cancel"
            >
              取消</button
            ><button class="button button-primary" :disabled="saving">
              {{ saving ? '正在保存…' : '保存修改' }}
            </button>
          </div>
        </form>

        <dl v-else class="info-list">
          <div>
            <dt>主队</dt>
            <dd>{{ home?.name }}</dd>
          </div>
          <div>
            <dt>客队</dt>
            <dd>{{ away?.name }}</dd>
          </div>
          <div>
            <dt>场馆</dt>
            <dd>{{ venue?.name }}</dd>
          </div>
          <div>
            <dt>地点</dt>
            <dd>{{ venue?.city }}</dd>
          </div>
        </dl>
        <p v-if="message" class="success">{{ message }}</p>
      </section>

      <section v-if="match" class="detail-card video-section">
        <div class="video-heading">
          <div>
            <p class="eyebrow">Match Video</p>
            <h2 class="section-title">比赛录像</h2>
            <p class="page-description">
              MP4 · 推荐 H.264 · 1080p；单文件上限
              {{ uploadPolicy ? formatBytes(uploadPolicy.max_size_bytes) : '10 GiB' }}；支持断点续传。
            </p>
          </div>
          <span v-if="videos.length" class="meta-chip">{{ videos.length }} 个视频</span>
        </div>

        <div v-if="!authStore.user" class="video-access-note">
          登录后可查看获授权的比赛录像；教练或分析师可以上传录像。
        </div>
        <template v-else-if="authStore.hasPermission('view_authorized_video')">
          <form
            v-if="authStore.hasPermission('upload_and_annotate_video')"
            class="upload-form"
            @submit.prevent="submitVideo"
          >
            <div class="field">
              <label for="match-video">选择 MP4 比赛录像</label>
              <input
                id="match-video"
                ref="videoInput"
                type="file"
                accept=".mp4,video/mp4"
                :disabled="uploading"
                @change="chooseVideo"
              />
            </div>
            <div class="field video-type-field">
              <label for="video-type">视频类型</label>
              <select id="video-type" v-model="selectedVideoType" :disabled="uploading">
                <option value="original">原始录像</option>
                <option value="supplementary">补充机位</option>
                <option value="processed">处理结果</option>
              </select>
            </div>
            <div v-if="selectedVideo" class="selected-file">
              <span>{{ selectedVideo.name }}</span>
              <strong>
                {{ formatDuration(selectedVideoDuration) }} · {{ formatBytes(selectedVideo.size) }}
              </strong>
            </div>
            <div v-if="uploading" class="progress-row" aria-live="polite">
              <progress :value="uploadProgress" max="100" />
              <span>{{ uploadProgress }}%</span>
            </div>
            <p v-if="videoError" class="error">{{ videoError }}</p>
            <p v-if="videoMessage" class="success">{{ videoMessage }}</p>
            <div class="filter-actions">
              <button
                class="button button-primary"
                type="submit"
                :disabled="uploading || !selectedVideo || Boolean(videoError)"
              >
                {{ uploading ? '正在上传…' : '上传并关联比赛' }}
              </button>
              <button
                v-if="uploading"
                class="button button-secondary"
                type="button"
                @click="cancelUpload"
              >
                取消上传
              </button>
            </div>
          </form>

          <div v-if="videos.length === 0" class="video-empty">本场比赛还没有上传录像。</div>
          <ul v-else class="video-list">
            <li v-for="video in videos" :key="video.id">
              <div class="video-info">
                <div class="video-title-row">
                  <strong>{{ video.original_filename }}</strong>
                  <span>{{ videoTypeLabels[video.video_type] }}</span>
                </div>
                <div class="video-metadata-row">
                  <span>时长 {{ formatDuration(video.duration_seconds) }}</span>
                  <span>大小 {{ formatBytes(video.size_bytes) }}</span>
                  <span>上传于 {{ formatUploadTime(video.created_at) }}</span>
                </div>
                <div class="video-status-row">
                  <span class="status-badge status-ready">uploaded</span>
                  <span
                    class="status-badge"
                    :class="processingClasses[video.processing_status]"
                  >
                    {{ processingLabels[video.processing_status] }}
                  </span>
                  <small>第 {{ video.processing_attempts }} 次处理</small>
                  <button
                    class="button button-secondary video-annotate-button"
                    type="button"
                    :disabled="video.processing_status !== 'completed'"
                    :title="
                      video.processing_status === 'completed'
                        ? '播放这段录像并进行人工标注'
                        : '视频处理完成后才能标注'
                    "
                    @click="selectPlaybackVideo(video)"
                  >
                    {{ selectedPlaybackVideoId === video.id ? '正在标注' : '播放并标注' }}
                  </button>
                  <button
                    v-if="authStore.hasPermission('upload_and_annotate_video')"
                    class="button button-danger video-delete-button"
                    type="button"
                    :disabled="
                      ['queued', 'processing'].includes(video.processing_status) ||
                      deletingVideoId === video.id
                    "
                    :title="
                      ['queued', 'processing'].includes(video.processing_status)
                        ? '处理任务运行期间不能删除'
                        : '删除视频'
                    "
                    @click="removeVideo(video)"
                  >
                    {{ deletingVideoId === video.id ? '删除中…' : '删除' }}
                  </button>
                </div>
                <div
                  v-if="['queued', 'processing'].includes(video.processing_status)"
                  class="processing-progress"
                >
                  <progress :value="video.processing_progress" max="100" />
                  <span>{{ video.processing_progress }}%</span>
                </div>
                <div v-if="video.failure_reason" class="processing-failure">
                  <span>{{ video.failure_reason }}</span>
                  <button
                    v-if="authStore.hasPermission('upload_and_annotate_video')"
                    class="button button-secondary"
                    type="button"
                    :disabled="retryingVideoId === video.id"
                    @click="retryProcessing(video)"
                  >
                    {{ retryingVideoId === video.id ? '正在重试…' : '重试处理' }}
                  </button>
                </div>
              </div>
            </li>
          </ul>
        </template>
        <div v-else class="video-access-note">当前账号没有查看比赛录像的权限。</div>
      </section>

      <section
        v-if="
          match &&
          authStore.hasPermission('view_authorized_video') &&
          (playbackVideo || events.length > 0)
        "
        class="detail-card annotation-section"
      >
        <div class="video-heading">
          <div>
            <p class="eyebrow">Manual Annotation</p>
            <h2 class="section-title">人工事件标注</h2>
            <p class="page-description">
              播放或暂停录像到事件发生的位置，再填写事件信息。保存时会自动记录当前视频时间。
            </p>
          </div>
          <span class="meta-chip">{{ events.length }} 条事件</span>
        </div>
        <p v-if="eventError" class="error annotation-global-message">{{ eventError }}</p>
        <p v-if="eventMessage" class="success annotation-global-message">{{ eventMessage }}</p>

        <div v-if="playbackVideo" class="annotation-workspace">
          <div class="annotation-player-panel">
            <strong>{{ playbackVideo.original_filename }}</strong>
            <video
              :key="playbackVideo.id"
              ref="videoPlayer"
              class="annotation-player"
              controls
              preload="metadata"
              :src="getVideoContentUrl(playbackVideo.id)"
              @loadedmetadata="applyPendingSeek"
              @timeupdate="updateCurrentVideoTime"
              @seeked="updateCurrentVideoTime"
            >
              当前浏览器不支持视频播放。
            </video>
            <div class="annotation-time">
              <span>当前时间</span>
              <strong>{{ formatDuration(currentVideoTime) }}</strong>
              <small>{{ currentVideoTime.toFixed(3) }} 秒</small>
            </div>
          </div>

          <form
            v-if="authStore.hasPermission('upload_and_annotate_video')"
            class="event-form"
            @submit.prevent="submitEvent"
          >
            <div v-if="editingEventId !== null" class="event-edit-heading">
              <strong>正在修改事件 #{{ editingEventId }}</strong>
              <button class="button button-secondary" type="button" @click="cancelEventEdit">
                取消修改
              </button>
            </div>
            <div class="field">
              <label for="event-timestamp">事件时间（秒）</label>
              <input
                id="event-timestamp"
                v-model.number="eventForm.timestamp_seconds"
                type="number"
                min="0"
                :max="playbackVideo.duration_seconds ?? undefined"
                step="0.001"
                required
                @change="seekFromEventTimestamp"
              />
            </div>
            <div class="field">
              <label for="event-type">事件类型</label>
              <select id="event-type" v-model="eventForm.event_type" required>
                <option
                  v-for="(label, value) in eventTypeLabels"
                  :key="value"
                  :value="value as EventType"
                >
                  {{ label }}
                </option>
              </select>
            </div>
            <div class="field">
              <label for="event-team">相关球队（可选）</label>
              <select id="event-team" v-model="eventForm.team_id">
                <option :value="null">不指定球队</option>
                <option v-if="home" :value="home.id">{{ home.name }}</option>
                <option v-if="away" :value="away.id">{{ away.name }}</option>
              </select>
            </div>
            <div class="field">
              <label for="event-player">相关球员（可选）</label>
              <select
                id="event-player"
                v-model="eventForm.player_id"
                @change="handlePlayerSelection"
              >
                <option :value="null">不指定球员</option>
                <option v-for="player in selectablePlayers" :key="player.id" :value="player.id">
                  {{ player.number }}号 · {{ player.name }}
                </option>
              </select>
            </div>
            <div class="field event-note-field">
              <label for="event-note">备注（可选）</label>
              <textarea
                id="event-note"
                v-model="eventForm.note"
                rows="3"
                maxlength="500"
                placeholder="例如：快攻右侧射门"
              />
            </div>
            <button class="button button-primary" type="submit" :disabled="eventSaving">
              {{
                eventSaving
                  ? '正在保存…'
                  : editingEventId === null
                    ? `保存 ${formatDuration(eventForm.timestamp_seconds)} 事件`
                    : '保存事件修改'
              }}
            </button>
          </form>
          <div v-else class="video-access-note">
            当前账号可以查看事件，但没有新增人工标注的权限。
          </div>
        </div>
        <div v-else class="video-access-note">
          请先在上方选择一段处理完成的视频，点击“播放并标注”。
        </div>

        <form class="event-filter-form" @submit.prevent="loadEvents">
          <div class="filter-grid">
            <div class="field">
              <label for="filter-event-type">事件类型</label>
              <select id="filter-event-type" v-model="eventFilters.event_type">
                <option value="">全部类型</option>
                <option v-for="(label, value) in eventTypeLabels" :key="value" :value="value">
                  {{ label }}
                </option>
              </select>
            </div>
            <div class="field">
              <label for="filter-event-team">球队</label>
              <select id="filter-event-team" v-model="eventFilters.team_id">
                <option :value="null">全部球队</option>
                <option v-if="home" :value="home.id">{{ home.name }}</option>
                <option v-if="away" :value="away.id">{{ away.name }}</option>
              </select>
            </div>
            <div class="field">
              <label for="filter-event-player">球员</label>
              <select id="filter-event-player" v-model="eventFilters.player_id">
                <option :value="null">全部球员</option>
                <option v-for="player in filterPlayers" :key="player.id" :value="player.id">
                  {{ player.number }}号 · {{ player.name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label for="filter-event-status">确认状态</label>
              <select id="filter-event-status" v-model="eventFilters.status">
                <option value="">全部状态</option>
                <option value="draft">待确认</option>
                <option value="verified">已确认</option>
              </select>
            </div>
          </div>
          <div class="filter-actions">
            <button class="button button-secondary" type="button" @click="resetEventFilters">
              清除筛选
            </button>
            <button class="button button-primary" type="submit">应用筛选</button>
          </div>
        </form>

        <div class="event-statistics" aria-live="polite">
          <div><span>当前结果</span><strong>{{ eventStatistics.total }}</strong></div>
          <div><span>已确认</span><strong>{{ eventStatistics.verified }}</strong></div>
          <div><span>待确认</span><strong>{{ eventStatistics.draft }}</strong></div>
        </div>

        <div class="event-list-heading">
          <h3>时间轴事件</h3>
          <span>筛选结果按视频时间从早到晚排列</span>
        </div>
        <div v-if="events.length === 0" class="video-empty">还没有人工事件标注。</div>
        <ol v-else class="event-list">
          <li v-for="event in events" :key="event.id">
            <time>{{ formatDuration(event.timestamp_seconds) }}</time>
            <div>
              <strong>{{ eventTypeLabels[event.event_type] }}</strong>
              <span>
                {{ teams.find((team) => team.id === event.team_id)?.short_name ?? '未指定球队' }}
                ·
                {{
                  players.find((player) => player.id === event.player_id)?.name ?? '未指定球员'
                }}
              </span>
              <p v-if="event.note">{{ event.note }}</p>
            </div>
            <div class="event-actions">
              <span
                class="status-badge"
                :class="event.status === 'verified' ? 'status-ready' : 'status-neutral'"
              >
                {{ event.status === 'verified' ? '已确认' : '待确认' }}
              </span>
              <button
                class="button button-secondary"
                type="button"
                @click="jumpToEvent(event)"
              >
                定位画面
              </button>
              <template v-if="authStore.hasPermission('upload_and_annotate_video')">
                <button
                  class="button button-secondary"
                  type="button"
                  :disabled="eventSaving || deletingEventId === event.id"
                  @click="startEditEvent(event)"
                >
                  编辑
                </button>
                <button
                  v-if="event.status !== 'verified'"
                  class="button button-primary"
                  type="button"
                  :disabled="verifyingEventId === event.id"
                  @click="confirmEvent(event)"
                >
                  {{ verifyingEventId === event.id ? '确认中…' : '确认' }}
                </button>
                <button
                  class="button button-danger"
                  type="button"
                  :disabled="deletingEventId === event.id"
                  @click="removeEvent(event)"
                >
                  {{ deletingEventId === event.id ? '删除中…' : '删除' }}
                </button>
              </template>
            </div>
          </li>
        </ol>
      </section>
    </main>
  </div>
</template>
<style scoped>
.detail-actions {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 16px;
}
.score {
  font-size: clamp(40px, 7vw, 68px);
  font-weight: 820;
}
.edit-form {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}
.error {
  color: var(--danger);
  font-weight: 650;
}
.success {
  color: var(--success);
  font-weight: 650;
}
.video-section { margin-top: 20px; }
.video-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.upload-form { margin-top: 22px; padding: 20px; border: 1px solid var(--border); border-radius: 14px; background: var(--surface-soft); }
.upload-form input[type='file'] { height: auto; padding: 10px; background: white; }
.video-type-field { margin-top: 14px; }
.selected-file,
.progress-row,
.video-list li { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.selected-file { margin-top: 12px; color: var(--muted-strong); font-size: 13px; }
.progress-row { margin-top: 14px; }
.progress-row progress { width: 100%; height: 12px; accent-color: var(--primary); }
.progress-row span { min-width: 42px; color: var(--primary-dark); font-weight: 750; text-align: right; }
.video-list { display: grid; gap: 10px; margin: 20px 0 0; padding: 0; list-style: none; }
.video-list li { padding: 16px; border: 1px solid var(--border); border-radius: 12px; }
.video-info { display: grid; width: 100%; gap: 12px; }
.video-title-row,
.video-metadata-row,
.video-status-row,
.processing-progress,
.processing-failure { display: flex; align-items: center; gap: 9px; }
.video-title-row { justify-content: space-between; }
.video-title-row span,
.video-metadata-row,
.video-status-row small { color: var(--muted); font-size: 12px; }
.video-metadata-row { display: flex; flex-wrap: wrap; gap: 8px 18px; }
.video-delete-button { margin-left: auto; padding: 7px 12px; }
.video-annotate-button { margin-left: auto; padding: 7px 12px; }
.video-annotate-button + .video-delete-button { margin-left: 0; }
.processing-progress progress { width: min(420px, 100%); height: 10px; accent-color: var(--primary); }
.processing-progress span { min-width: 38px; color: var(--primary-dark); font-size: 12px; font-weight: 750; }
.processing-failure { justify-content: space-between; padding: 12px; border-radius: 10px; color: var(--danger); background: var(--danger-soft); }
.processing-failure span { font-size: 13px; font-weight: 650; }
.video-empty,
.video-access-note { margin-top: 20px; padding: 18px; border-radius: 12px; color: var(--muted-strong); background: var(--surface-soft); }
.annotation-section { margin-top: 20px; }
.annotation-global-message { margin: 16px 0 0; }
.annotation-workspace { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.8fr); gap: 22px; margin-top: 22px; }
.annotation-player-panel,
.event-form { padding: 18px; border: 1px solid var(--border); border-radius: 14px; background: var(--surface-soft); }
.annotation-player { display: block; width: 100%; max-height: 560px; margin-top: 12px; border-radius: 10px; background: #111827; }
.annotation-time { display: flex; align-items: baseline; gap: 12px; margin-top: 12px; }
.annotation-time span,
.annotation-time small { color: var(--muted); }
.annotation-time strong { color: var(--primary-dark); font-size: 22px; }
.event-form { display: grid; align-content: start; gap: 14px; }
.event-edit-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.event-form textarea { width: 100%; resize: vertical; }
.event-filter-form { margin-top: 26px; padding: 18px; border: 1px solid var(--border); border-radius: 14px; background: var(--surface-soft); }
.event-filter-form .filter-actions { margin-top: 14px; }
.event-statistics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }
.event-statistics div { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 13px 15px; border: 1px solid var(--border); border-radius: 12px; }
.event-statistics span { color: var(--muted); font-size: 13px; }
.event-statistics strong { color: var(--primary-dark); font-size: 20px; }
.event-list-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-top: 28px; }
.event-list-heading h3 { margin: 0; }
.event-list-heading span { color: var(--muted); font-size: 13px; }
.event-list { display: grid; gap: 10px; margin: 14px 0 0; padding: 0; list-style: none; }
.event-list li { display: grid; grid-template-columns: 78px 1fr auto; align-items: start; gap: 14px; padding: 14px 16px; border: 1px solid var(--border); border-radius: 12px; }
.event-list time { color: var(--primary-dark); font-size: 18px; font-weight: 800; }
.event-list li > div { display: grid; gap: 5px; }
.event-list li > div span { color: var(--muted); font-size: 13px; }
.event-list p { margin: 0; color: var(--muted-strong); }
.event-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 7px; }
.event-actions .button { padding: 6px 10px; }
@media (max-width: 620px) {
  .detail-actions {
    align-items: flex-start;
  }
  .video-heading,
  .video-list li,
  .video-title-row,
  .video-metadata-row,
  .processing-failure { align-items: flex-start; flex-direction: column; }
  .annotation-workspace { grid-template-columns: 1fr; }
  .event-statistics { grid-template-columns: 1fr; }
  .event-list li { grid-template-columns: 68px 1fr; }
  .event-list li > .status-badge { grid-column: 2; justify-self: start; }
  .event-actions { grid-column: 2; justify-content: flex-start; }
}
</style>
