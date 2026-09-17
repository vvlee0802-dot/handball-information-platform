<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import ApiMatchTable from '@/components/ApiMatchTable.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import {
  getTeam,
  deleteTeam,
  listTeams,
  teamGenderLabels,
  updateTeam,
  type TeamInput,
  type TeamRecord,
} from '@/services/teams'
import { listPlayers, type PlayerRecord } from '@/services/players'
import { listMatches, type MatchRecord } from '@/services/matches'
import { listCompetitions, type CompetitionRecord } from '@/services/competitions'
import { listVenues, type VenueRecord } from '@/services/venues'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const team = ref<TeamRecord | null>(null)
const isLoading = ref(true)
const isEditing = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const saveError = ref('')
const saveMessage = ref('')
const editForm = reactive<TeamInput>({
  name: '',
  short_name: '',
  city: '',
  country: '',
  gender: 'men',
  description: '',
})
const players = ref<PlayerRecord[]>([]),
  matches = ref<MatchRecord[]>([]),
  competitions = ref<CompetitionRecord[]>([]),
  venues = ref<VenueRecord[]>([]),
  allTeams = ref<TeamRecord[]>([])

const fillForm = (record: TeamRecord) =>
  Object.assign(editForm, {
    name: record.name,
    short_name: record.short_name,
    city: record.city,
    country: record.country,
    gender: record.gender,
    description: record.description ?? '',
  })

const loadTeam = async () => {
  const teamId = Number(route.params.teamId)
  if (!Number.isInteger(teamId) || teamId <= 0) {
    isLoading.value = false
    return
  }
  try {
    const [record, playerRows, matchRows, competitionRows, venueRows, teamRows] = await Promise.all(
      [
        getTeam(teamId),
        listPlayers(teamId),
        listMatches(),
        listCompetitions(),
        listVenues(),
        listTeams(),
      ],
    )
    team.value = record
    players.value = playerRows
    matches.value = matchRows.filter(
      (item) => item.home_team_id === teamId || item.away_team_id === teamId,
    )
    competitions.value = competitionRows
    venues.value = venueRows
    allTeams.value = teamRows
    fillForm(team.value)
  } catch {
    team.value = null
  } finally {
    isLoading.value = false
  }
}

const startEditing = () => {
  if (!team.value) return
  fillForm(team.value)
  saveError.value = ''
  saveMessage.value = ''
  isEditing.value = true
}

const cancelEditing = () => {
  if (team.value) fillForm(team.value)
  saveError.value = ''
  isEditing.value = false
}

const handleUpdate = async () => {
  if (!team.value) return
  saveError.value = ''
  saveMessage.value = ''
  isSaving.value = true
  try {
    const updated = await updateTeam(team.value.id, {
      ...editForm,
      description: editForm.description || null,
    })
    team.value = updated
    fillForm(updated)
    isEditing.value = false
    saveMessage.value = '球队信息已保存。'
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '球队保存失败'
  } finally {
    isSaving.value = false
  }
}

const handleDelete = async () => {
  if (!team.value) return
  if (!window.confirm(`确定删除球队“${team.value.name}”吗？删除后无法恢复。`)) return
  saveError.value = ''
  isDeleting.value = true
  try {
    await deleteTeam(team.value.id)
    await router.push({ name: 'teams' })
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '球队删除失败'
  } finally {
    isDeleting.value = false
  }
}

onMounted(loadTeam)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/teams">← 返回球队列表</RouterLink>
      <div v-if="isLoading" class="detail-card empty-state">正在从后端加载球队…</div>
      <NotFoundPanel v-else-if="!team" entity="球队" />
      <template v-else>
        <section class="detail-card">
          <div class="detail-header">
            <div>
              <p class="eyebrow">Team</p>
              <h1 class="detail-title">{{ team.name }}</h1>
              <p class="page-description">{{ team.description || '暂未填写球队简介。' }}</p>
            </div>
            <div class="detail-actions">
              <span class="meta-chip">{{ teamGenderLabels[team.gender] }}</span
              ><button
                v-if="!isEditing && authStore.hasPermission('manage_competition_data')"
                class="button button-secondary"
                type="button"
                @click="startEditing"
              >
                编辑球队
              </button>
              <button
                v-if="!isEditing && authStore.hasPermission('manage_competition_data')"
                class="button button-danger"
                type="button"
                :disabled="isDeleting"
                @click="handleDelete"
              >
                {{ isDeleting ? '删除中…' : '删除球队' }}
              </button>
            </div>
          </div>

          <p v-if="!isEditing && saveError" class="form-message form-message-error">
            删除失败：{{ saveError }}
          </p>

          <form v-if="isEditing" class="edit-form" @submit.prevent="handleUpdate">
            <div class="filter-grid">
              <div class="field">
                <label for="edit-team-name">球队名称</label
                ><input id="edit-team-name" v-model="editForm.name" required maxlength="120" />
              </div>
              <div class="field">
                <label for="edit-team-short-name">简称</label
                ><input
                  id="edit-team-short-name"
                  v-model="editForm.short_name"
                  required
                  maxlength="50"
                />
              </div>
              <div class="field">
                <label for="edit-team-country">国家或地区</label
                ><input id="edit-team-country" v-model="editForm.country" required maxlength="80" />
              </div>
              <div class="field">
                <label for="edit-team-city">所在城市</label
                ><input id="edit-team-city" v-model="editForm.city" required maxlength="80" />
              </div>
              <div class="field">
                <label for="edit-team-gender">组别</label
                ><select id="edit-team-gender" v-model="editForm.gender">
                  <option value="men">男子</option>
                  <option value="women">女子</option>
                </select>
              </div>
              <div class="field field-wide">
                <label for="edit-team-description">简介</label
                ><input id="edit-team-description" v-model="editForm.description" maxlength="500" />
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
              <dt>简称</dt>
              <dd>{{ team.short_name }}</dd>
            </div>
            <div>
              <dt>国家或地区</dt>
              <dd>{{ team.country }}</dd>
            </div>
            <div>
              <dt>所在城市</dt>
              <dd>{{ team.city }}</dd>
            </div>
          </dl>
          <p v-if="saveMessage" class="form-message form-message-success" aria-live="polite">
            {{ saveMessage }}
          </p>
        </section>
        <section class="linked-section">
          <h2 class="section-title">球队阵容</h2>
          <div v-if="players.length" class="table-panel">
            <table class="data-table">
              <thead>
                <tr>
                  <th>号码</th>
                  <th>球员</th>
                  <th>位置</th>
                  <th>出生日期</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="player in players" :key="player.id">
                  <td>#{{ player.number }}</td>
                  <td>
                    <RouterLink :to="{ name: 'player-detail', params: { playerId: player.id } }">{{
                      player.name
                    }}</RouterLink>
                  </td>
                  <td>{{ player.position }}</td>
                  <td>{{ player.birth_date }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="panel empty-state">暂无球员。</div>
        </section>
        <section class="linked-section">
          <h2 class="section-title">相关比赛</h2>
          <ApiMatchTable
            :rows="matches"
            :competitions="competitions"
            :teams="allTeams"
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
.field-wide {
  grid-column: span 3;
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
    grid-column: span 1;
  }
}
@media (max-width: 620px) {
  .detail-actions {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
