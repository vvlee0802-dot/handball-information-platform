<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import ApiMatchTable from '@/components/ApiMatchTable.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import {
  competitionStatusLabels,
  getCompetition,
  updateCompetition,
  type CompetitionInput,
  type CompetitionRecord,
} from '@/services/competitions'
import { listMatches, type MatchRecord } from '@/services/matches'
import { listTeams, type TeamRecord } from '@/services/teams'
import { listVenues, type VenueRecord } from '@/services/venues'

const route = useRoute()
const competition = ref<CompetitionRecord | null>(null)
const isLoading = ref(true)
const errorMessage = ref('')
const isEditing = ref(false)
const isSaving = ref(false)
const saveError = ref('')
const saveMessage = ref('')
const editForm = reactive<CompetitionInput>({
  name: '',
  season: '',
  stage: '',
  status: 'draft',
})
const matches = ref<MatchRecord[]>([]),
  teams = ref<TeamRecord[]>([]),
  venues = ref<VenueRecord[]>([])

const fillEditForm = (record: CompetitionRecord) => {
  editForm.name = record.name
  editForm.season = record.season
  editForm.stage = record.stage ?? ''
  editForm.status = record.status
}

const loadCompetition = async () => {
  const competitionId = Number(route.params.competitionId)
  if (!Number.isInteger(competitionId) || competitionId <= 0) {
    errorMessage.value = '赛事编号无效'
    isLoading.value = false
    return
  }

  try {
    const [record, allMatches, teamRows, venueRows] = await Promise.all([
      getCompetition(competitionId),
      listMatches(),
      listTeams(),
      listVenues(),
    ])
    competition.value = record
    matches.value = allMatches.filter((item) => item.competition_id === competitionId)
    teams.value = teamRows
    venues.value = venueRows
    fillEditForm(competition.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '赛事加载失败'
  } finally {
    isLoading.value = false
  }
}

const startEditing = () => {
  if (!competition.value) return

  fillEditForm(competition.value)
  saveError.value = ''
  saveMessage.value = ''
  isEditing.value = true
}

const cancelEditing = () => {
  if (competition.value) fillEditForm(competition.value)

  saveError.value = ''
  isEditing.value = false
}

const handleUpdate = async () => {
  if (!competition.value) return

  saveError.value = ''
  saveMessage.value = ''
  isSaving.value = true

  try {
    const updated = await updateCompetition(competition.value.id, {
      ...editForm,
      stage: editForm.stage || null,
    })
    competition.value = updated
    fillEditForm(updated)
    isEditing.value = false
    saveMessage.value = '赛事信息已保存。'
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '赛事保存失败'
  } finally {
    isSaving.value = false
  }
}

onMounted(loadCompetition)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/competitions">← 返回赛事列表</RouterLink>
      <div v-if="isLoading" class="detail-card empty-state">正在从后端加载赛事…</div>
      <NotFoundPanel v-else-if="!competition" entity="赛事" />
      <template v-else>
        <section class="detail-card">
          <div class="detail-header">
            <div>
              <p class="eyebrow">Competition</p>
              <h1 class="detail-title">{{ competition.name }}</h1>
              <p class="page-description">赛事数据由 FastAPI 从 PostgreSQL 读取。</p>
            </div>
            <div class="detail-actions">
              <span class="status-badge status-neutral">{{
                competitionStatusLabels[competition.status]
              }}</span>
              <button
                v-if="!isEditing"
                class="button button-secondary"
                type="button"
                @click="startEditing"
              >
                编辑赛事
              </button>
            </div>
          </div>

          <form v-if="isEditing" class="edit-form" @submit.prevent="handleUpdate">
            <div class="filter-grid">
              <div class="field">
                <label for="edit-competition-name">赛事名称</label>
                <input
                  id="edit-competition-name"
                  v-model="editForm.name"
                  type="text"
                  required
                  maxlength="120"
                />
              </div>
              <div class="field">
                <label for="edit-competition-season">赛季</label>
                <input
                  id="edit-competition-season"
                  v-model="editForm.season"
                  type="text"
                  required
                  maxlength="50"
                />
              </div>
              <div class="field">
                <label for="edit-competition-stage">赛事阶段</label>
                <input
                  id="edit-competition-stage"
                  v-model="editForm.stage"
                  type="text"
                  maxlength="80"
                />
              </div>
              <div class="field">
                <label for="edit-competition-status">状态</label>
                <select id="edit-competition-status" v-model="editForm.status">
                  <option value="draft">草稿</option>
                  <option value="active">进行中</option>
                  <option value="completed">已结束</option>
                  <option value="archived">已归档</option>
                </select>
              </div>
            </div>

            <p v-if="saveError" class="form-message form-message-error">
              保存失败：{{ saveError }}
            </p>

            <div class="filter-actions">
              <button
                class="button button-secondary"
                type="button"
                :disabled="isSaving"
                @click="cancelEditing"
              >
                取消
              </button>
              <button class="button button-primary" type="submit" :disabled="isSaving">
                {{ isSaving ? '正在保存…' : '保存修改' }}
              </button>
            </div>
          </form>

          <dl v-else class="info-list">
            <div>
              <dt>赛季</dt>
              <dd>{{ competition.season }}</dd>
            </div>
            <div>
              <dt>赛事阶段</dt>
              <dd>{{ competition.stage || '暂未设置' }}</dd>
            </div>
          </dl>
          <p v-if="saveMessage" class="form-message form-message-success" aria-live="polite">
            {{ saveMessage }}
          </p>
        </section>
        <section class="linked-section">
          <div class="page-heading">
            <div>
              <h2 class="section-title">赛事比赛</h2>
              <p class="page-description">该赛事在数据库中的全部比赛。</p>
            </div>
          </div>
          <ApiMatchTable
            :rows="matches"
            :competitions="[competition]"
            :teams="teams"
            :venues="venues"
          />
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.detail-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.edit-form {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}

.form-message {
  margin: 16px 0 0;
  font-weight: 650;
}

.form-message-error {
  color: var(--danger);
}

.form-message-success {
  color: var(--success);
}

@media (max-width: 620px) {
  .detail-actions {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
