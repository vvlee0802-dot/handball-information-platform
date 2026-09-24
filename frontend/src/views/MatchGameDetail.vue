<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import {
  completedWithoutCandidates,
  isLowConfidenceCandidate,
  listAnalysisPredictions,
  listMatchAnalysisTasks,
  reviewAnalysisPrediction,
  startVideoAnalysis,
  type AnalysisPredictionOutcome,
  type AnalysisPredictionRecord,
  type AnalysisTaskRecord,
  type AnalysisTaskStatus,
} from '@/services/analysisTasks'
import {
  createClipExport,
  deleteClipExport,
  getClipExportContentUrl,
  listMatchClipExports,
  type ClipExportRecord,
  type ClipExportStatus,
} from '@/services/clipExports'
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
const analysisTasks = ref<AnalysisTaskRecord[]>([])
const startingAnalysisVideoId = ref<number | null>(null)
const analysisError = ref('')
const analysisMessage = ref('')
const expandedAnalysisTaskId = ref<string | null>(null)
const analysisPredictions = ref<AnalysisPredictionRecord[]>([])
const analysisPredictionFilter = ref<'all' | AnalysisPredictionOutcome>('all')
const analysisPredictionLoading = ref(false)
const analysisPredictionError = ref('')
const reviewingAnalysisPredictionId = ref<number | null>(null)
const uploadProgress = ref(0)
const uploading = ref(false)
const retryingVideoId = ref<number | null>(null)
const deletingVideoId = ref<number | null>(null)
const events = ref<MatchEventRecord[]>([])
const selectedPlaybackVideoId = ref<number | null>(null)
const videoPlayer = ref<HTMLVideoElement | null>(null)
const annotationFullscreenContainer = ref<HTMLElement | null>(null)
const annotationFullscreenActive = ref(false)
const quickAnnotationOpen = ref(false)
const quickAnnotationWasPlaying = ref(false)
const quickAnnotationPosition = reactive({ x: 24, y: 80 })
const currentVideoTime = ref(0)
const eventSaving = ref(false)
const editingEventId = ref<number | null>(null)
const deletingEventId = ref<number | null>(null)
const verifyingEventId = ref<number | null>(null)
const pendingSeekTime = ref<number | null>(null)
const eventError = ref('')
const eventMessage = ref('')
const clipExports = ref<ClipExportRecord[]>([])
const selectedClipEventIds = ref<number[]>([])
const creatingClipExport = ref(false)
const deletingClipExportId = ref<number | null>(null)
const previewClipExportId = ref<number | null>(null)
const clipError = ref('')
const clipMessage = ref('')
let videoPollTimer: ReturnType<typeof setTimeout> | null = null
let analysisPollTimer: ReturnType<typeof setTimeout> | null = null
let clipPollTimer: ReturnType<typeof setTimeout> | null = null
let activeUploadController: AbortController | null = null
let quickAnnotationDrag:
  | {
      pointerId: number
      startX: number
      startY: number
      originX: number
      originY: number
      moved: boolean
    }
  | null = null
let suppressQuickAnnotationClick = false
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
const quickAnnotationExpandsLeft = computed(() => {
  const width = annotationFullscreenContainer.value?.clientWidth ?? window.innerWidth
  return quickAnnotationPosition.x >= width / 2
})
const quickAnnotationPositionStyle = computed(() => ({
  left: `${quickAnnotationPosition.x}px`,
  top: `${quickAnnotationPosition.y}px`,
}))
const quickAnnotationPanelStyle = computed(() => {
  const width = annotationFullscreenContainer.value?.clientWidth ?? window.innerWidth
  const availableWidth = quickAnnotationExpandsLeft.value
    ? quickAnnotationPosition.x + 128 - 16
    : width - quickAnnotationPosition.x - 16
  return { width: `${Math.max(320, Math.min(1120, availableWidth))}px` }
})
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
const filteredAnalysisPredictions = computed(() =>
  analysisPredictionFilter.value === 'all'
    ? analysisPredictions.value
    : analysisPredictions.value.filter(
        (prediction) => prediction.outcome === analysisPredictionFilter.value,
      ),
)
const selectedVerifiedEvents = computed(() =>
  events.value.filter(
    (event) =>
      event.status === 'verified' && selectedClipEventIds.value.includes(event.id),
  ),
)
const scoresEnabled = computed(() => form.status === 'live' || form.status === 'completed')
const processingLabels: Record<VideoProcessingStatus, string> = {
  queued: '等待处理',
  processing: '处理中',
  completed: '处理完成',
  failed: '处理失败',
}
const analysisStatusLabels: Record<AnalysisTaskStatus, string> = {
  queued: '等待 AI 分析',
  running: 'AI 分析中',
  completed: '分析任务完成',
  failed: '分析任务失败',
}
const analysisStageLabels: Record<string, string> = {
  queued: '等待后台任务',
  preparing: '准备视频',
  scanning_frames: '扫描视频帧',
  completed: '视频帧扫描完成',
  completed_evaluation: '整场模型评估完成',
  completed_no_model: '帧扫描完成，等待接入训练模型',
  failed: '处理失败',
}
const analysisPredictionOutcomeLabels: Record<AnalysisPredictionOutcome, string> = {
  true_positive: '命中',
  false_positive: '误报',
  false_negative: '漏检',
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
const clipStatusLabels: Record<ClipExportStatus, string> = {
  queued: '等待处理',
  processing: '正在生成',
  completed: '可以预览和下载',
  failed: '生成失败',
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

const latestAnalysisTask = (videoId: number) =>
  analysisTasks.value.find((task) => task.video_id === videoId) ?? null

const scheduleAnalysisPolling = () => {
  if (analysisPollTimer) clearTimeout(analysisPollTimer)
  analysisPollTimer = null
  if (analysisTasks.value.some((task) => ['queued', 'running'].includes(task.status))) {
    analysisPollTimer = setTimeout(() => void loadAnalysisTasks(), 1500)
  }
}

const loadAnalysisTasks = async () => {
  if (!match.value || !authStore.hasPermission('view_authorized_video')) return
  const hadActiveTask = analysisTasks.value.some((task) =>
    ['queued', 'running'].includes(task.status),
  )
  try {
    analysisTasks.value = await listMatchAnalysisTasks(match.value.id)
    if (
      hadActiveTask &&
      !analysisTasks.value.some((task) => ['queued', 'running'].includes(task.status))
    ) {
      await loadEvents()
    }
  } catch (e) {
    analysisError.value = e instanceof Error ? e.message : 'AI 分析任务加载失败'
  } finally {
    scheduleAnalysisPolling()
  }
}

const startAnalysis = async (video: VideoRecord) => {
  startingAnalysisVideoId.value = video.id
  analysisError.value = ''
  analysisMessage.value = ''
  try {
    const task = await startVideoAnalysis(video.id)
    analysisMessage.value = task.reused
      ? `该视频已有运行中的任务，继续显示任务 ${task.id}。`
      : `已创建 AI 分析任务 ${task.id}。`
    await loadAnalysisTasks()
  } catch (e) {
    analysisError.value = e instanceof Error ? e.message : 'AI 分析任务启动失败'
  } finally {
    startingAnalysisVideoId.value = null
  }
}

const toggleAnalysisPredictions = async (task: AnalysisTaskRecord) => {
  if (expandedAnalysisTaskId.value === task.id) {
    expandedAnalysisTaskId.value = null
    analysisPredictions.value = []
    return
  }
  expandedAnalysisTaskId.value = task.id
  analysisPredictionFilter.value = 'all'
  analysisPredictionLoading.value = true
  analysisPredictionError.value = ''
  try {
    analysisPredictions.value = await listAnalysisPredictions(task.id)
  } catch (e) {
    analysisPredictions.value = []
    analysisPredictionError.value = e instanceof Error ? e.message : 'AI 识别明细加载失败'
  } finally {
    analysisPredictionLoading.value = false
  }
}

const reviewFalsePositive = async (
  prediction: AnalysisPredictionRecord,
  decision: 'include' | 'exclude',
) => {
  reviewingAnalysisPredictionId.value = prediction.id
  analysisPredictionError.value = ''
  try {
    const updated = await reviewAnalysisPrediction(prediction.id, decision)
    analysisPredictions.value = analysisPredictions.value.map((item) =>
      item.id === updated.id ? updated : item,
    )
  } catch (e) {
    analysisPredictionError.value = e instanceof Error ? e.message : '训练样本审核失败'
  } finally {
    reviewingAnalysisPredictionId.value = null
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
    const selectableIds = new Set(
      events.value.filter((event) => event.status === 'verified').map((event) => event.id),
    )
    selectedClipEventIds.value = selectedClipEventIds.value.filter((id) => selectableIds.has(id))
  } catch (e) {
    eventError.value = e instanceof Error ? e.message : '事件记录加载失败'
  }
}

const scheduleClipPolling = () => {
  if (clipPollTimer) clearTimeout(clipPollTimer)
  clipPollTimer = null
  if (clipExports.value.some((task) => ['queued', 'processing'].includes(task.status))) {
    clipPollTimer = setTimeout(() => void loadClipExports(), 1500)
  }
}

const loadClipExports = async () => {
  if (!match.value || !authStore.hasPermission('view_authorized_video')) return
  try {
    clipExports.value = await listMatchClipExports(match.value.id)
    if (
      previewClipExportId.value !== null &&
      !clipExports.value.some(
        (task) => task.id === previewClipExportId.value && task.status === 'completed',
      )
    ) {
      previewClipExportId.value = null
    }
  } catch (e) {
    clipError.value = e instanceof Error ? e.message : '片段任务加载失败'
  } finally {
    scheduleClipPolling()
  }
}

const submitClipExport = async () => {
  if (!match.value || selectedVerifiedEvents.value.length === 0) return
  creatingClipExport.value = true
  clipError.value = ''
  clipMessage.value = ''
  try {
    await createClipExport(
      match.value.id,
      selectedVerifiedEvents.value.map((event) => event.id),
    )
    clipMessage.value = `已提交 ${selectedVerifiedEvents.value.length} 个事件的片段任务。`
    selectedClipEventIds.value = []
    await loadClipExports()
  } catch (e) {
    clipError.value = e instanceof Error ? e.message : '片段任务创建失败'
  } finally {
    creatingClipExport.value = false
  }
}

const removeClipExport = async (task: ClipExportRecord) => {
  if (['queued', 'processing'].includes(task.status)) return
  if (!window.confirm(`确定删除导出片段“${task.filename}”吗？原始录像和事件不会删除。`)) {
    return
  }
  deletingClipExportId.value = task.id
  clipError.value = ''
  clipMessage.value = ''
  try {
    await deleteClipExport(task.id)
    if (previewClipExportId.value === task.id) previewClipExportId.value = null
    clipMessage.value = `已删除导出片段“${task.filename}”。`
    await loadClipExports()
  } catch (e) {
    clipError.value = e instanceof Error ? e.message : '片段删除失败'
  } finally {
    deletingClipExportId.value = null
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

const resetManualEventForm = () => {
  editingEventId.value = null
  eventForm.event_type = 'goal'
  eventForm.team_id = null
  eventForm.player_id = null
  eventForm.note = null
}

const positionQuickAnnotationAtRight = () => {
  const container = annotationFullscreenContainer.value
  if (!container) return
  quickAnnotationPosition.x = Math.max(16, container.clientWidth - 152)
  quickAnnotationPosition.y = Math.max(
    16,
    Math.min(container.clientHeight - 72, container.clientHeight / 2 - 28),
  )
}

const handleAnnotationFullscreenChange = () => {
  annotationFullscreenActive.value =
    document.fullscreenElement === annotationFullscreenContainer.value
  if (annotationFullscreenActive.value) {
    void nextTick(positionQuickAnnotationAtRight)
  } else {
    quickAnnotationOpen.value = false
    quickAnnotationDrag = null
  }
}

const toggleAnnotationFullscreen = async () => {
  const container = annotationFullscreenContainer.value
  if (!container) return
  eventError.value = ''
  try {
    if (document.fullscreenElement === container) {
      await document.exitFullscreen()
    } else {
      await container.requestFullscreen()
    }
  } catch {
    eventError.value = '浏览器无法进入全屏标注模式，请检查全屏权限后重试。'
  }
}

const clampQuickAnnotationPosition = (x: number, y: number) => {
  const container = annotationFullscreenContainer.value
  if (!container) return
  quickAnnotationPosition.x = Math.max(12, Math.min(x, container.clientWidth - 140))
  quickAnnotationPosition.y = Math.max(12, Math.min(y, container.clientHeight - 64))
}

const startQuickAnnotationDrag = (event: PointerEvent) => {
  if (quickAnnotationOpen.value) return
  quickAnnotationDrag = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: quickAnnotationPosition.x,
    originY: quickAnnotationPosition.y,
    moved: false,
  }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

const moveQuickAnnotation = (event: PointerEvent) => {
  if (!quickAnnotationDrag || quickAnnotationDrag.pointerId !== event.pointerId) return
  const deltaX = event.clientX - quickAnnotationDrag.startX
  const deltaY = event.clientY - quickAnnotationDrag.startY
  if (Math.abs(deltaX) > 4 || Math.abs(deltaY) > 4) quickAnnotationDrag.moved = true
  clampQuickAnnotationPosition(
    quickAnnotationDrag.originX + deltaX,
    quickAnnotationDrag.originY + deltaY,
  )
}

const finishQuickAnnotationDrag = (event: PointerEvent) => {
  if (!quickAnnotationDrag || quickAnnotationDrag.pointerId !== event.pointerId) return
  suppressQuickAnnotationClick = quickAnnotationDrag.moved
  ;(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId)
  quickAnnotationDrag = null
  window.setTimeout(() => {
    suppressQuickAnnotationClick = false
  }, 0)
}

const beginQuickAnnotation = () => {
  if (suppressQuickAnnotationClick || !videoPlayer.value) return
  quickAnnotationWasPlaying.value = !videoPlayer.value.paused
  videoPlayer.value.pause()
  updateCurrentVideoTime()
  resetManualEventForm()
  eventForm.timestamp_seconds = Number(currentVideoTime.value.toFixed(3))
  eventError.value = ''
  eventMessage.value = ''
  quickAnnotationOpen.value = true
}

const resumeAfterQuickAnnotation = async () => {
  quickAnnotationOpen.value = false
  resetManualEventForm()
  if (!quickAnnotationWasPlaying.value || !videoPlayer.value) return
  try {
    await videoPlayer.value.play()
  } catch {
    eventMessage.value = '标注已结束，请点击播放器继续播放。'
  }
}

const cancelQuickAnnotation = async () => {
  eventError.value = ''
  eventMessage.value = ''
  await resumeAfterQuickAnnotation()
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

const showTimestampInPlayer = async (
  videoId: number,
  timestampSeconds: number,
): Promise<boolean> => {
  const video = videos.value.find((item) => item.id === videoId)
  if (!video) {
    eventError.value = '该识别结果关联的视频当前不可用。'
    return false
  }
  const validationError = validateEventTimestamp(timestampSeconds, video.duration_seconds)
  if (validationError) {
    eventError.value = validationError
    return false
  }
  selectedPlaybackVideoId.value = video.id
  editingEventId.value = null
  eventForm.video_id = video.id
  eventForm.timestamp_seconds = timestampSeconds
  currentVideoTime.value = timestampSeconds
  pendingSeekTime.value = timestampSeconds
  eventError.value = ''
  eventMessage.value = ''
  await nextTick()
  applyPendingSeek()
  videoPlayer.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  return true
}

const showEventInPlayer = async (event: MatchEventRecord): Promise<boolean> =>
  showTimestampInPlayer(event.video_id, event.timestamp_seconds)

const jumpToEvent = async (event: MatchEventRecord) => {
  await showEventInPlayer(event)
}

const jumpToAnalysisPrediction = async (
  prediction: AnalysisPredictionRecord,
  videoId: number,
) => {
  const timestamp =
    prediction.predicted_timestamp_seconds ?? prediction.ground_truth_timestamp_seconds
  if (timestamp === null) return
  await showTimestampInPlayer(videoId, timestamp)
}

const submitEvent = async (): Promise<boolean> => {
  if (!match.value || !playbackVideo.value) return false
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
      const created = await createMatchEvent(match.value.id, {
        video_id: playbackVideo.value.id,
        ...payload,
      })
      eventMessage.value = `已在 ${formatDuration(created.timestamp_seconds)} 保存并确认人工事件。`
    } else {
      const updated = await updateMatchEvent(match.value.id, editingEventId.value, payload)
      eventMessage.value =
        updated.status === 'verified'
          ? `已更新并确认 ${formatDuration(updated.timestamp_seconds)} 的人工事件。`
          : `已更新 ${formatDuration(updated.timestamp_seconds)} 的 AI 候选，请继续确认。`
      editingEventId.value = null
    }
    resetManualEventForm()
    await loadEvents()
    return true
  } catch (e) {
    eventError.value = e instanceof Error ? e.message : '事件保存失败'
    return false
  } finally {
    eventSaving.value = false
  }
}

const submitQuickAnnotation = async () => {
  if (await submitEvent()) await resumeAfterQuickAnnotation()
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
    void loadAnalysisTasks()
    void loadEvents()
    void loadClipExports()
    void loadUploadPolicy()
  },
  { immediate: true },
)
onMounted(() => {
  document.addEventListener('fullscreenchange', handleAnnotationFullscreenChange)
  void load()
})
onUnmounted(() => {
  if (videoPollTimer) clearTimeout(videoPollTimer)
  if (analysisPollTimer) clearTimeout(analysisPollTimer)
  if (clipPollTimer) clearTimeout(clipPollTimer)
  activeUploadController?.abort()
  document.removeEventListener('fullscreenchange', handleAnnotationFullscreenChange)
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
            <p class="page-description">
              视频处理完成后可启动 AI 分析任务；任务编号、真实状态和进度会保存到数据库。
            </p>
          </div>
          <span v-if="videos.length" class="meta-chip">{{ videos.length }} 个视频</span>
        </div>

        <aside class="ai-boundary-note" role="note" aria-label="AI 分析支持边界">
          <strong>AI 分析支持边界</strong>
          <p>
            当前进球模型仅针对与训练样本相似的清晰横向转播机位进行验证。侧后方机位、严重遮挡、低清晰度、回放和不同转播风格都可能降低准确率。
          </p>
          <p>
            AI 结果只用于生成待审核候选，不会自动进入正式统计；未发现候选也不代表比赛一定没有进球。
          </p>
        </aside>

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
          <p v-if="analysisError" class="error">{{ analysisError }}</p>
          <p v-if="analysisMessage" class="success">{{ analysisMessage }}</p>
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
                    class="button button-secondary"
                    type="button"
                    :disabled="
                      video.processing_status !== 'completed' ||
                      startingAnalysisVideoId === video.id ||
                      ['queued', 'running'].includes(
                        latestAnalysisTask(video.id)?.status ?? '',
                      )
                    "
                    :title="
                      ['queued', 'running'].includes(
                        latestAnalysisTask(video.id)?.status ?? '',
                      )
                        ? '该视频已有运行中的 AI 分析任务'
                        : '启动后台 AI 分析任务'
                    "
                    @click="startAnalysis(video)"
                  >
                    {{
                      startingAnalysisVideoId === video.id
                        ? '正在启动…'
                        : ['queued', 'running'].includes(
                              latestAnalysisTask(video.id)?.status ?? '',
                            )
                          ? 'AI 分析运行中'
                          : '启动 AI 分析'
                    }}
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
                <div
                  v-if="latestAnalysisTask(video.id)"
                  class="analysis-task-row"
                  aria-live="polite"
                >
                  <div class="analysis-task-heading">
                    <div>
                      <strong>
                        {{ analysisStatusLabels[latestAnalysisTask(video.id)!.status] }}
                      </strong>
                      <span>
                        {{ analysisStageLabels[latestAnalysisTask(video.id)!.stage] ?? latestAnalysisTask(video.id)!.stage }}
                      </span>
                      <span>
                        候选 {{ latestAnalysisTask(video.id)!.candidate_count }} 条 ·
                        模型 {{ latestAnalysisTask(video.id)!.model_version ?? '尚未接入' }}
                      </span>
                      <div
                        v-if="latestAnalysisTask(video.id)!.evaluation_mode"
                        class="analysis-evaluation"
                      >
                        <strong>整场评估</strong>
                        <span>
                          命中 {{ latestAnalysisTask(video.id)!.true_positive_count }} /
                          {{ latestAnalysisTask(video.id)!.ground_truth_count }} ·
                          漏检 {{ latestAnalysisTask(video.id)!.false_negative_count }} ·
                          误报 {{ latestAnalysisTask(video.id)!.false_positive_count }}
                        </span>
                        <span>
                          Precision
                          {{ ((latestAnalysisTask(video.id)!.precision ?? 0) * 100).toFixed(1) }}% ·
                          Recall
                          {{ ((latestAnalysisTask(video.id)!.recall ?? 0) * 100).toFixed(1) }}% ·
                          F1 {{ ((latestAnalysisTask(video.id)!.f1 ?? 0) * 100).toFixed(1) }}%
                        </span>
                        <span v-if="latestAnalysisTask(video.id)!.mean_absolute_error_seconds !== null">
                          平均时间偏差
                          {{ latestAnalysisTask(video.id)!.mean_absolute_error_seconds!.toFixed(2) }} 秒
                        </span>
                        <button
                          class="button button-secondary analysis-detail-toggle"
                          type="button"
                          @click="toggleAnalysisPredictions(latestAnalysisTask(video.id)!)"
                        >
                          {{
                            expandedAnalysisTaskId === latestAnalysisTask(video.id)!.id
                              ? '收起识别明细'
                              : '查看识别明细'
                          }}
                        </button>
                      </div>
                    </div>
                    <code>{{ latestAnalysisTask(video.id)!.id }}</code>
                  </div>
                  <div
                    v-if="expandedAnalysisTaskId === latestAnalysisTask(video.id)!.id"
                    class="analysis-prediction-panel"
                  >
                    <p v-if="analysisPredictionLoading" class="page-description">
                      正在加载识别明细…
                    </p>
                    <p v-else-if="analysisPredictionError" class="error">
                      {{ analysisPredictionError }}
                    </p>
                    <template v-else>
                      <div class="analysis-prediction-filters">
                        <button
                          v-for="filter in [
                            { value: 'all', label: '全部' },
                            { value: 'true_positive', label: '命中' },
                            { value: 'false_positive', label: '误报' },
                            { value: 'false_negative', label: '漏检' },
                          ] as const"
                          :key="filter.value"
                          class="button button-secondary"
                          :class="{ active: analysisPredictionFilter === filter.value }"
                          type="button"
                          @click="analysisPredictionFilter = filter.value"
                        >
                          {{ filter.label }}
                        </button>
                      </div>
                      <p v-if="analysisPredictions.length === 0" class="page-description">
                        该任务只保存了汇总指标，请重新运行一次 AI 分析生成明细。
                      </p>
                      <p
                        v-else-if="filteredAnalysisPredictions.length === 0"
                        class="page-description"
                      >
                        当前筛选下没有识别结果。
                      </p>
                      <ul v-else class="analysis-prediction-list">
                        <li
                          v-for="prediction in filteredAnalysisPredictions"
                          :key="prediction.id"
                          class="analysis-prediction-item"
                        >
                          <div>
                            <strong>
                              {{ analysisPredictionOutcomeLabels[prediction.outcome] }}
                            </strong>
                            <span v-if="prediction.predicted_timestamp_seconds !== null">
                              AI {{ formatDuration(prediction.predicted_timestamp_seconds) }}
                            </span>
                            <span v-if="prediction.ground_truth_timestamp_seconds !== null">
                              人工 {{ formatDuration(prediction.ground_truth_timestamp_seconds) }}
                            </span>
                            <span v-if="prediction.confidence !== null">
                              置信度 {{ (prediction.confidence * 100).toFixed(1) }}%
                            </span>
                            <span
                              v-if="isLowConfidenceCandidate(prediction.confidence)"
                              class="confidence-warning"
                            >
                              低置信度，必须人工确认
                            </span>
                            <span v-if="prediction.time_error_seconds !== null">
                              偏差 {{ prediction.time_error_seconds.toFixed(2) }} 秒
                            </span>
                            <span v-if="prediction.outcome === 'false_positive'">
                              训练处理：{{
                                prediction.training_decision === 'pending'
                                  ? '待审核'
                                  : prediction.training_decision === 'include'
                                    ? '已加入困难负样本'
                                    : '已排除'
                              }}
                            </span>
                          </div>
                          <div class="analysis-prediction-actions">
                            <button
                              class="button button-secondary"
                              type="button"
                              @click="jumpToAnalysisPrediction(prediction, video.id)"
                            >
                              定位视频
                            </button>
                            <template
                              v-if="
                                prediction.outcome === 'false_positive' &&
                                authStore.hasPermission('upload_and_annotate_video')
                              "
                            >
                              <button
                                class="button button-primary"
                                type="button"
                                :disabled="reviewingAnalysisPredictionId === prediction.id"
                                @click="reviewFalsePositive(prediction, 'include')"
                              >
                                加入训练集
                              </button>
                              <button
                                class="button button-secondary"
                                type="button"
                                :disabled="reviewingAnalysisPredictionId === prediction.id"
                                @click="reviewFalsePositive(prediction, 'exclude')"
                              >
                                排除
                              </button>
                            </template>
                          </div>
                        </li>
                      </ul>
                    </template>
                  </div>
                  <p
                    v-if="completedWithoutCandidates(latestAnalysisTask(video.id)!)"
                    class="analysis-empty-warning"
                  >
                    本次分析未发现候选。这不代表比赛一定没有进球，请继续人工检查录像或使用人工标注。
                  </p>
                  <div class="processing-progress">
                    <progress :value="latestAnalysisTask(video.id)!.progress" max="100" />
                    <span>{{ latestAnalysisTask(video.id)!.progress }}%</span>
                  </div>
                  <small v-if="latestAnalysisTask(video.id)!.failure_reason" class="error">
                    {{ latestAnalysisTask(video.id)!.failure_reason }}
                  </small>
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
              播放或暂停录像到事件发生的位置，再填写事件信息。人工标注保存后会直接确认。
            </p>
          </div>
          <span class="meta-chip">{{ events.length }} 条事件</span>
        </div>
        <p v-if="eventError" class="error annotation-global-message">{{ eventError }}</p>
        <p v-if="eventMessage" class="success annotation-global-message">{{ eventMessage }}</p>

        <div v-if="playbackVideo" class="annotation-workspace">
          <div class="annotation-player-panel">
            <strong>{{ playbackVideo.original_filename }}</strong>
            <div
              ref="annotationFullscreenContainer"
              class="annotation-fullscreen-container"
              :class="{ 'is-fullscreen': annotationFullscreenActive }"
            >
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

              <div
                v-if="
                  annotationFullscreenActive &&
                  authStore.hasPermission('upload_and_annotate_video')
                "
                class="quick-annotation-anchor"
                :style="quickAnnotationPositionStyle"
              >
                <button
                  v-if="!quickAnnotationOpen"
                  class="quick-annotation-trigger"
                  type="button"
                  :aria-expanded="quickAnnotationOpen"
                  @click="beginQuickAnnotation"
                  @pointerdown="startQuickAnnotationDrag"
                  @pointermove="moveQuickAnnotation"
                  @pointerup="finishQuickAnnotationDrag"
                  @pointercancel="finishQuickAnnotationDrag"
                >
                  <span>标注事件</span>
                  <small>{{ formatDuration(currentVideoTime) }}</small>
                </button>

                <form
                  v-else
                  class="quick-annotation-panel"
                  :class="
                    quickAnnotationExpandsLeft
                      ? 'quick-annotation-panel--left'
                      : 'quick-annotation-panel--right'
                  "
                  :style="quickAnnotationPanelStyle"
                  @submit.prevent="submitQuickAnnotation"
                >
                  <div class="quick-annotation-field quick-annotation-time-field">
                    <label for="quick-event-timestamp">事件时间</label>
                    <input
                      id="quick-event-timestamp"
                      v-model.number="eventForm.timestamp_seconds"
                      type="number"
                      min="0"
                      :max="playbackVideo.duration_seconds ?? undefined"
                      step="0.001"
                      required
                      @change="seekFromEventTimestamp"
                    />
                  </div>
                  <div class="quick-annotation-field">
                    <label for="quick-event-type">事件类型</label>
                    <select id="quick-event-type" v-model="eventForm.event_type" required>
                      <option
                        v-for="(label, value) in eventTypeLabels"
                        :key="value"
                        :value="value as EventType"
                      >
                        {{ label }}
                      </option>
                    </select>
                  </div>
                  <div class="quick-annotation-field">
                    <label for="quick-event-team">相关球队</label>
                    <select id="quick-event-team" v-model="eventForm.team_id">
                      <option :value="null">不指定球队</option>
                      <option v-if="home" :value="home.id">{{ home.name }}</option>
                      <option v-if="away" :value="away.id">{{ away.name }}</option>
                    </select>
                  </div>
                  <div class="quick-annotation-field">
                    <label for="quick-event-player">相关球员</label>
                    <select
                      id="quick-event-player"
                      v-model="eventForm.player_id"
                      @change="handlePlayerSelection"
                    >
                      <option :value="null">不指定球员</option>
                      <option
                        v-for="player in selectablePlayers"
                        :key="player.id"
                        :value="player.id"
                      >
                        {{ player.number }}号 · {{ player.name }}
                      </option>
                    </select>
                  </div>
                  <div class="quick-annotation-field quick-annotation-note-field">
                    <label for="quick-event-note">备注</label>
                    <input
                      id="quick-event-note"
                      v-model="eventForm.note"
                      type="text"
                      maxlength="500"
                      placeholder="可选备注"
                    />
                  </div>
                  <div class="quick-annotation-actions">
                    <button
                      class="button button-secondary"
                      type="button"
                      :disabled="eventSaving"
                      @click="cancelQuickAnnotation"
                    >
                      取消
                    </button>
                    <button class="button button-primary" type="submit" :disabled="eventSaving">
                      {{ eventSaving ? '保存中…' : '保存并继续' }}
                    </button>
                  </div>
                </form>
              </div>
            </div>
            <div class="annotation-player-toolbar">
              <div class="annotation-time">
                <span>当前时间</span>
                <strong>{{ formatDuration(currentVideoTime) }}</strong>
                <small>{{ currentVideoTime.toFixed(3) }} 秒</small>
              </div>
              <button
                class="button button-secondary"
                type="button"
                @click="toggleAnnotationFullscreen"
              >
                {{ annotationFullscreenActive ? '退出全屏标注' : '进入全屏标注' }}
              </button>
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
              <span v-if="event.source === 'ai'" class="ai-candidate-meta">
                AI 候选 · 置信度
                {{ event.confidence === null ? '未知' : `${(event.confidence * 100).toFixed(1)}%` }}
                · 模型 {{ event.model_version ?? '未知' }}
              </span>
              <span
                v-if="event.source === 'ai' && isLowConfidenceCandidate(event.confidence)"
                class="confidence-warning"
              >
                低置信度，必须人工确认
              </span>
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
              <label
                v-if="
                  event.status === 'verified' &&
                  authStore.hasPermission('upload_and_annotate_video')
                "
                class="clip-event-choice"
              >
                <input v-model="selectedClipEventIds" type="checkbox" :value="event.id" />
                选入片段
              </label>
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

        <section class="clip-export-panel">
          <div class="video-heading">
            <div>
              <p class="eyebrow">Event Clips</p>
              <h3>事件片段导出</h3>
              <p class="page-description">
                只能选择已确认事件。每个事件默认截取前 8 秒和后 5 秒，多选时会按比赛时间顺序合并。
              </p>
            </div>
            <span class="meta-chip">{{ clipExports.length }} 个任务</span>
          </div>

          <div
            v-if="authStore.hasPermission('upload_and_annotate_video')"
            class="clip-export-create"
          >
            <span>已选择 {{ selectedVerifiedEvents.length }} 个已确认事件</span>
            <button
              class="button button-primary"
              type="button"
              :disabled="creatingClipExport || selectedVerifiedEvents.length === 0"
              @click="submitClipExport"
            >
              {{ creatingClipExport ? '正在提交…' : '生成并导出 MP4' }}
            </button>
          </div>
          <p v-if="clipError" class="error">{{ clipError }}</p>
          <p v-if="clipMessage" class="success">{{ clipMessage }}</p>

          <div v-if="clipExports.length === 0" class="video-empty">
            还没有片段导出任务。请先确认事件，再勾选需要导出的内容。
          </div>
          <ul v-else class="clip-export-list">
            <li v-for="task in clipExports" :key="task.id">
              <div>
                <strong>{{ task.filename }}</strong>
                <span>
                  {{ task.event_ids.length }} 个事件 ·
                  {{ formatDuration(task.duration_seconds) }} ·
                  {{ task.size_bytes === null ? '等待生成文件' : formatBytes(task.size_bytes) }}
                </span>
                <small v-if="task.failure_reason">{{ task.failure_reason }}</small>
              </div>
              <div class="clip-export-actions">
                <span
                  class="status-badge"
                  :class="
                    task.status === 'completed'
                      ? 'status-ready'
                      : task.status === 'failed'
                        ? 'status-failed'
                        : 'status-processing'
                  "
                >
                  {{ clipStatusLabels[task.status] }}
                </span>
                <button
                  v-if="task.status === 'completed'"
                  class="button button-secondary"
                  type="button"
                  @click="previewClipExportId = task.id"
                >
                  预览
                </button>
                <a
                  v-if="task.status === 'completed'"
                  class="button button-primary"
                  :href="getClipExportContentUrl(task.id, true)"
                >
                  下载 MP4
                </a>
                <button
                  v-if="authStore.hasPermission('upload_and_annotate_video')"
                  class="button button-danger"
                  type="button"
                  :disabled="
                    ['queued', 'processing'].includes(task.status) ||
                    deletingClipExportId === task.id
                  "
                  :title="
                    ['queued', 'processing'].includes(task.status)
                      ? '任务处理完成后才能删除'
                      : '删除导出任务和生成的 MP4，不影响原始录像与事件'
                  "
                  @click="removeClipExport(task)"
                >
                  {{ deletingClipExportId === task.id ? '删除中…' : '删除' }}
                </button>
              </div>
            </li>
          </ul>

          <div v-if="previewClipExportId !== null" class="clip-preview">
            <div class="event-edit-heading">
              <strong>片段预览</strong>
              <button
                class="button button-secondary"
                type="button"
                @click="previewClipExportId = null"
              >
                关闭预览
              </button>
            </div>
            <video
              :key="previewClipExportId"
              class="annotation-player"
              controls
              preload="metadata"
              :src="getClipExportContentUrl(previewClipExportId)"
            >
              当前浏览器不支持视频播放。
            </video>
          </div>
        </section>
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
.ai-boundary-note { display: grid; gap: 6px; margin-top: 18px; padding: 14px 16px; border: 1px solid #f2c66d; border-radius: 12px; color: #6b4b0b; background: #fff8e8; }
.ai-boundary-note strong { color: #7a4b00; }
.ai-boundary-note p { margin: 0; font-size: 13px; line-height: 1.55; }
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
.analysis-task-row { display: grid; gap: 10px; padding: 13px 14px; border: 1px solid var(--border); border-radius: 10px; background: var(--surface-soft); }
.analysis-task-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.analysis-task-heading > div { display: grid; gap: 3px; }
.analysis-task-heading span { color: var(--muted); font-size: 12px; }
.analysis-evaluation { display: grid; gap: 3px; margin-top: 6px; padding: 8px 10px; border-radius: 8px; background: var(--surface); }
.analysis-evaluation strong { color: var(--primary-dark); font-size: 12px; }
.analysis-detail-toggle { width: fit-content; margin-top: 6px; }
.analysis-prediction-panel { display: grid; gap: 10px; padding: 12px; border-top: 1px solid var(--border); }
.analysis-prediction-filters { display: flex; flex-wrap: wrap; gap: 8px; }
.analysis-prediction-filters .active { border-color: var(--primary); color: var(--primary-dark); background: var(--primary-soft); }
.analysis-prediction-list { display: grid; gap: 8px; max-height: 440px; margin: 0; padding: 0; overflow: auto; list-style: none; }
.analysis-prediction-item { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
.analysis-prediction-item > div:first-child { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; }
.analysis-prediction-item span { color: var(--muted); font-size: 12px; }
.confidence-warning { width: fit-content; padding: 2px 7px; border-radius: 999px; color: #8a4b08 !important; background: #fff0c7; font-size: 11px !important; font-weight: 750; }
.analysis-empty-warning { margin: 0; padding: 10px 12px; border-radius: 8px; color: #7a4b00; background: #fff8e8; font-size: 12px; line-height: 1.5; }
.analysis-prediction-actions { display: flex; flex-shrink: 0; flex-wrap: wrap; gap: 6px; }
.analysis-task-heading code { max-width: 250px; overflow: hidden; color: var(--muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.video-empty,
.video-access-note { margin-top: 20px; padding: 18px; border-radius: 12px; color: var(--muted-strong); background: var(--surface-soft); }
.annotation-section { margin-top: 20px; }
.annotation-global-message { margin: 16px 0 0; }
.annotation-workspace { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.8fr); gap: 22px; margin-top: 22px; }
.annotation-player-panel,
.event-form { padding: 18px; border: 1px solid var(--border); border-radius: 14px; background: var(--surface-soft); }
.annotation-fullscreen-container { position: relative; margin-top: 12px; overflow: hidden; border-radius: 10px; background: #030712; }
.annotation-fullscreen-container.is-fullscreen { display: flex; width: 100vw; height: 100vh; align-items: center; justify-content: center; border-radius: 0; }
.annotation-player { display: block; width: 100%; max-height: 560px; border-radius: 10px; background: #111827; }
.annotation-fullscreen-container.is-fullscreen .annotation-player { width: 100%; height: 100%; max-height: none; border-radius: 0; object-fit: contain; }
.annotation-player-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 12px; }
.annotation-time { display: flex; align-items: baseline; gap: 12px; margin-top: 12px; }
.annotation-player-toolbar .annotation-time { margin-top: 0; }
.annotation-time span,
.annotation-time small { color: var(--muted); }
.annotation-time strong { color: var(--primary-dark); font-size: 22px; }
.quick-annotation-anchor { position: absolute; z-index: 20; width: 128px; pointer-events: none; }
.quick-annotation-trigger { display: grid; width: 128px; min-height: 52px; padding: 8px 14px; border: 1px solid rgb(255 255 255 / 28%); border-radius: 999px; color: white; background: rgb(37 80 218 / 92%); box-shadow: 0 12px 30px rgb(0 0 0 / 35%); cursor: grab; pointer-events: auto; touch-action: none; user-select: none; }
.quick-annotation-trigger:active { cursor: grabbing; }
.quick-annotation-trigger span { font-size: 14px; font-weight: 800; }
.quick-annotation-trigger small { color: rgb(255 255 255 / 78%); font-size: 11px; }
.quick-annotation-panel { position: absolute; top: 0; display: grid; grid-template-columns: 118px 130px minmax(150px, 1fr) minmax(160px, 1fr) minmax(170px, 1.3fr) auto; align-items: end; gap: 10px; padding: 12px; border: 1px solid rgb(255 255 255 / 24%); border-radius: 14px; background: rgb(15 23 42 / 96%); box-shadow: 0 18px 50px rgb(0 0 0 / 48%); pointer-events: auto; }
.quick-annotation-panel--left { right: 0; }
.quick-annotation-panel--right { left: 0; }
.quick-annotation-field { display: grid; min-width: 0; gap: 5px; }
.quick-annotation-field label { color: rgb(255 255 255 / 72%); font-size: 11px; font-weight: 700; }
.quick-annotation-field input,
.quick-annotation-field select { width: 100%; min-width: 0; height: 38px; padding: 7px 9px; border-color: rgb(255 255 255 / 22%); color: #f8fafc; background: #1e293b; }
.quick-annotation-field select option { color: #111827; background: white; }
.quick-annotation-actions { display: flex; gap: 8px; }
.quick-annotation-actions .button { height: 38px; padding: 7px 11px; white-space: nowrap; }
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
.event-list .ai-candidate-meta { color: var(--primary-dark); font-weight: 700; }
.event-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 7px; }
.event-actions .button { padding: 6px 10px; }
.clip-event-choice { display: inline-flex; align-items: center; gap: 6px; color: var(--muted-strong); font-size: 13px; font-weight: 650; }
.clip-event-choice input { width: auto; }
.clip-export-panel { margin-top: 30px; padding-top: 26px; border-top: 1px solid var(--border); }
.clip-export-panel h3 { margin: 0; }
.clip-export-create { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-top: 18px; padding: 14px 16px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-soft); }
.clip-export-create span { color: var(--muted-strong); font-weight: 650; }
.clip-export-list { display: grid; gap: 10px; margin: 16px 0 0; padding: 0; list-style: none; }
.clip-export-list li { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 15px 16px; border: 1px solid var(--border); border-radius: 12px; }
.clip-export-list li > div:first-child { display: grid; gap: 5px; }
.clip-export-list span { color: var(--muted); font-size: 13px; }
.clip-export-list small { color: var(--danger); font-weight: 650; }
.clip-export-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 8px; }
.clip-export-actions .button { padding: 7px 11px; text-decoration: none; }
.clip-preview { margin-top: 18px; padding: 18px; border: 1px solid var(--border); border-radius: 14px; background: var(--surface-soft); }
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
  .annotation-player-toolbar { align-items: flex-start; flex-direction: column; }
  .event-statistics { grid-template-columns: 1fr; }
  .event-list li { grid-template-columns: 68px 1fr; }
  .event-list li > .status-badge { grid-column: 2; justify-self: start; }
  .event-actions { grid-column: 2; justify-content: flex-start; }
  .clip-export-create,
  .clip-export-list li { align-items: flex-start; flex-direction: column; }
  .clip-export-actions { justify-content: flex-start; }
}
</style>
