<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { listCompetitions, type CompetitionRecord } from '@/services/competitions'
import {
  getMatch,
  matchStatusLabels,
  updateMatch,
  type MatchInput,
  type MatchRecord,
} from '@/services/matches'
import { listTeams, type TeamRecord } from '@/services/teams'
import { listVenues, type VenueRecord } from '@/services/venues'
import {
  deleteVideo,
  formatBytes,
  formatDuration,
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
const match = ref<MatchRecord | null>(null)
const competitions = ref<CompetitionRecord[]>([])
const teams = ref<TeamRecord[]>([])
const venues = ref<VenueRecord[]>([])
const loading = ref(true),
  editing = ref(false),
  saving = ref(false)
const error = ref(''),
  message = ref('')
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
const competition = computed(() =>
  competitions.value.find((x) => x.id === match.value?.competition_id),
)
const home = computed(() => teams.value.find((x) => x.id === match.value?.home_team_id))
const away = computed(() => teams.value.find((x) => x.id === match.value?.away_team_id))
const venue = computed(() => venues.value.find((x) => x.id === match.value?.venue_id))
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
    const [record, cs, ts, vs] = await Promise.all([
      getMatch(Number(route.params.matchId)),
      listCompetitions(),
      listTeams(),
      listVenues(),
    ])
    match.value = record
    competitions.value = cs
    teams.value = ts
    venues.value = vs
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

const loadVideos = async () => {
  if (!match.value || !authStore.hasPermission('view_authorized_video')) return
  try {
    videos.value = await listMatchVideos(match.value.id)
  } catch (e) {
    videoError.value = e instanceof Error ? e.message : '视频记录加载失败'
  } finally {
    scheduleVideoPolling()
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
          </div>
        </div>

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
.processing-progress progress { width: min(420px, 100%); height: 10px; accent-color: var(--primary); }
.processing-progress span { min-width: 38px; color: var(--primary-dark); font-size: 12px; font-weight: 750; }
.processing-failure { justify-content: space-between; padding: 12px; border-radius: 10px; color: var(--danger); background: var(--danger-soft); }
.processing-failure span { font-size: 13px; font-weight: 650; }
.video-empty,
.video-access-note { margin-top: 20px; padding: 18px; border-radius: 12px; color: var(--muted-strong); background: var(--surface-soft); }
@media (max-width: 620px) {
  .detail-actions {
    align-items: flex-start;
  }
  .video-heading,
  .video-list li,
  .video-title-row,
  .video-metadata-row,
  .processing-failure { align-items: flex-start; flex-direction: column; }
}
</style>
