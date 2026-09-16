<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import ApiMatchTable from '@/components/ApiMatchTable.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { getVenue, updateVenue, type VenueInput, type VenueRecord } from '@/services/venues'
import { listMatches, type MatchRecord } from '@/services/matches'
import { listCompetitions, type CompetitionRecord } from '@/services/competitions'
import { listTeams, type TeamRecord } from '@/services/teams'

const route = useRoute()
const venue = ref<VenueRecord | null>(null)
const isLoading = ref(true)
const isEditing = ref(false)
const isSaving = ref(false)
const saveError = ref('')
const saveMessage = ref('')
const editForm = reactive<VenueInput>({
  name: '',
  city: '',
  address: '',
  capacity: 0,
  description: '',
})
const matches = ref<MatchRecord[]>([]),
  competitions = ref<CompetitionRecord[]>([]),
  teams = ref<TeamRecord[]>([])

const fillForm = (record: VenueRecord) =>
  Object.assign(editForm, {
    name: record.name,
    city: record.city,
    address: record.address,
    capacity: record.capacity,
    description: record.description ?? '',
  })

const loadVenue = async () => {
  const venueId = Number(route.params.venueId)
  if (!Number.isInteger(venueId) || venueId <= 0) {
    isLoading.value = false
    return
  }
  try {
    const [record, matchRows, competitionRows, teamRows] = await Promise.all([
      getVenue(venueId),
      listMatches(),
      listCompetitions(),
      listTeams(),
    ])
    venue.value = record
    matches.value = matchRows.filter((item) => item.venue_id === venueId)
    competitions.value = competitionRows
    teams.value = teamRows
    fillForm(venue.value)
  } catch {
    venue.value = null
  } finally {
    isLoading.value = false
  }
}

const startEditing = () => {
  if (!venue.value) return
  fillForm(venue.value)
  saveError.value = ''
  saveMessage.value = ''
  isEditing.value = true
}

const cancelEditing = () => {
  if (venue.value) fillForm(venue.value)
  saveError.value = ''
  isEditing.value = false
}

const handleUpdate = async () => {
  if (!venue.value) return
  saveError.value = ''
  saveMessage.value = ''
  isSaving.value = true
  try {
    const updated = await updateVenue(venue.value.id, {
      ...editForm,
      description: editForm.description || null,
    })
    venue.value = updated
    fillForm(updated)
    isEditing.value = false
    saveMessage.value = '场馆信息已保存。'
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '场馆保存失败'
  } finally {
    isSaving.value = false
  }
}

onMounted(loadVenue)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/venues">← 返回场馆列表</RouterLink>
      <div v-if="isLoading" class="detail-card empty-state">正在从后端加载场馆…</div>
      <NotFoundPanel v-else-if="!venue" entity="场馆" />
      <template v-else>
        <section class="detail-card">
          <div class="detail-header">
            <div>
              <p class="eyebrow">Venue</p>
              <h1 class="detail-title">{{ venue.name }}</h1>
              <p class="page-description">{{ venue.description || '暂未填写场馆简介。' }}</p>
            </div>
            <div class="detail-actions">
              <span class="meta-chip">{{ venue.city }}</span
              ><button
                v-if="!isEditing"
                class="button button-secondary"
                type="button"
                @click="startEditing"
              >
                编辑场馆
              </button>
            </div>
          </div>

          <form v-if="isEditing" class="edit-form" @submit.prevent="handleUpdate">
            <div class="filter-grid">
              <div class="field">
                <label for="edit-venue-name">场馆名称</label
                ><input id="edit-venue-name" v-model="editForm.name" required maxlength="120" />
              </div>
              <div class="field">
                <label for="edit-venue-city">所在城市</label
                ><input id="edit-venue-city" v-model="editForm.city" required maxlength="80" />
              </div>
              <div class="field">
                <label for="edit-venue-address">详细地址</label
                ><input
                  id="edit-venue-address"
                  v-model="editForm.address"
                  required
                  maxlength="200"
                />
              </div>
              <div class="field">
                <label for="edit-venue-capacity">容量</label
                ><input
                  id="edit-venue-capacity"
                  v-model.number="editForm.capacity"
                  type="number"
                  required
                  min="0"
                  max="1000000"
                />
              </div>
              <div class="field field-wide">
                <label for="edit-venue-description">简介</label
                ><input
                  id="edit-venue-description"
                  v-model="editForm.description"
                  maxlength="500"
                />
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
                取消</button
              ><button class="button button-primary" type="submit" :disabled="isSaving">
                {{ isSaving ? '正在保存…' : '保存修改' }}
              </button>
            </div>
          </form>

          <dl v-else class="info-list">
            <div>
              <dt>所在城市</dt>
              <dd>{{ venue.city }}</dd>
            </div>
            <div>
              <dt>地址</dt>
              <dd>{{ venue.address }}</dd>
            </div>
            <div>
              <dt>容量</dt>
              <dd>{{ venue.capacity.toLocaleString('zh-CN') }} 人</dd>
            </div>
          </dl>
          <p v-if="saveMessage" class="form-message form-message-success" aria-live="polite">
            {{ saveMessage }}
          </p>
        </section>
        <section class="linked-section">
          <h2 class="section-title">场馆比赛</h2>
          <ApiMatchTable
            :rows="matches"
            :competitions="competitions"
            :teams="teams"
            :venues="venue ? [venue] : []"
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
.field-wide {
  grid-column: span 4;
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
@media (max-width: 900px) {
  .field-wide {
    grid-column: span 2;
  }
}
@media (max-width: 620px) {
  .field-wide {
    grid-column: span 1;
  }
  .detail-actions {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
