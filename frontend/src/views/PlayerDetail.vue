<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import {
  deletePlayer,
  getPlayer,
  updatePlayer,
  type PlayerInput,
  type PlayerRecord,
} from '@/services/players'
import { listTeams, type TeamRecord } from '@/services/teams'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const player = ref<PlayerRecord | null>(null)
const teams = ref<TeamRecord[]>([])
const isLoading = ref(true)
const isEditing = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const saveError = ref('')
const saveMessage = ref('')
const editForm = reactive<PlayerInput>({
  name: '',
  number: 0,
  position: '',
  team_id: 0,
  birth_date: '',
  description: '',
})
const team = computed(() => teams.value.find((item) => item.id === player.value?.team_id))

const fillForm = (record: PlayerRecord) =>
  Object.assign(editForm, {
    name: record.name,
    number: record.number,
    position: record.position,
    team_id: record.team_id,
    birth_date: record.birth_date,
    description: record.description ?? '',
  })

const loadData = async () => {
  const playerId = Number(route.params.playerId)
  if (!Number.isInteger(playerId) || playerId <= 0) {
    isLoading.value = false
    return
  }
  try {
    const [record, teamRows] = await Promise.all([getPlayer(playerId), listTeams()])
    player.value = record
    teams.value = teamRows
    fillForm(record)
  } catch {
    player.value = null
  } finally {
    isLoading.value = false
  }
}

const startEditing = () => {
  if (!player.value) return
  fillForm(player.value)
  saveError.value = ''
  saveMessage.value = ''
  isEditing.value = true
}

const cancelEditing = () => {
  if (player.value) fillForm(player.value)
  saveError.value = ''
  isEditing.value = false
}

const handleUpdate = async () => {
  if (!player.value) return
  saveError.value = ''
  saveMessage.value = ''
  isSaving.value = true
  try {
    const updated = await updatePlayer(player.value.id, {
      ...editForm,
      description: editForm.description || null,
    })
    player.value = updated
    fillForm(updated)
    isEditing.value = false
    saveMessage.value = '球员信息已保存。'
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '球员保存失败'
  } finally {
    isSaving.value = false
  }
}

const handleDelete = async () => {
  if (!player.value) return
  if (!window.confirm(`确定删除球员“${player.value.name}”吗？删除后无法恢复。`)) return
  saveError.value = ''
  isDeleting.value = true
  try {
    await deletePlayer(player.value.id)
    await router.push({ name: 'players' })
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '球员删除失败'
  } finally {
    isDeleting.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/players">← 返回球员列表</RouterLink>
      <div v-if="isLoading" class="detail-card empty-state">正在从后端加载球员…</div>
      <NotFoundPanel v-else-if="!player" entity="球员" />
      <template v-else>
        <section class="detail-card">
          <div class="detail-header">
            <div>
              <p class="eyebrow">Player</p>
              <h1 class="detail-title">{{ player.name }}</h1>
              <p class="page-description">{{ player.description || '暂未填写球员简介。' }}</p>
            </div>
            <div class="detail-actions">
              <span class="meta-chip">#{{ player.number }}</span
              ><button
                v-if="!isEditing && authStore.hasPermission('manage_competition_data')"
                class="button button-secondary"
                type="button"
                @click="startEditing"
              >
                编辑球员
              </button>
              <button
                v-if="!isEditing && authStore.hasPermission('manage_competition_data')"
                class="button button-danger"
                type="button"
                :disabled="isDeleting"
                @click="handleDelete"
              >
                {{ isDeleting ? '删除中…' : '删除球员' }}
              </button>
            </div>
          </div>

          <p v-if="!isEditing && saveError" class="form-message form-message-error">
            删除失败：{{ saveError }}
          </p>

          <form v-if="isEditing" class="edit-form" @submit.prevent="handleUpdate">
            <div class="filter-grid">
              <div class="field">
                <label for="edit-player-name">球员姓名</label
                ><input id="edit-player-name" v-model="editForm.name" required maxlength="120" />
              </div>
              <div class="field">
                <label for="edit-player-number">号码</label
                ><input
                  id="edit-player-number"
                  v-model.number="editForm.number"
                  type="number"
                  required
                  min="0"
                  max="99"
                />
              </div>
              <div class="field">
                <label for="edit-player-position">位置</label
                ><input
                  id="edit-player-position"
                  v-model="editForm.position"
                  required
                  maxlength="50"
                />
              </div>
              <div class="field">
                <label for="edit-player-team">所属球队</label
                ><select id="edit-player-team" v-model.number="editForm.team_id" required>
                  <option v-for="item in teams" :key="item.id" :value="item.id">
                    {{ item.name }}
                  </option>
                </select>
              </div>
              <div class="field">
                <label for="edit-player-birth-date">出生日期</label
                ><input
                  id="edit-player-birth-date"
                  v-model="editForm.birth_date"
                  type="date"
                  required
                />
              </div>
              <div class="field field-wide">
                <label for="edit-player-description">简介</label
                ><input
                  id="edit-player-description"
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
              <dt>位置</dt>
              <dd>{{ player.position }}</dd>
            </div>
            <div>
              <dt>出生日期</dt>
              <dd>{{ player.birth_date }}</dd>
            </div>
            <div>
              <dt>所属球队</dt>
              <dd>
                <RouterLink v-if="team" :to="{ name: 'team-detail', params: { teamId: team.id } }"
                  >{{ team.name }} →</RouterLink
                ><span v-else>未知球队</span>
              </dd>
            </div>
            <div>
              <dt>球队所在城市</dt>
              <dd>{{ team?.city || '—' }}</dd>
            </div>
          </dl>
          <p v-if="saveMessage" class="form-message form-message-success" aria-live="polite">
            {{ saveMessage }}
          </p>
        </section>
        <section class="detail-card phase-note">
          <p class="eyebrow">Later Epic</p>
          <h2 class="section-title">个人比赛分析</h2>
          <p>进球、射门、扑救等个人统计会在比赛事件与 AI 分析功能完成后接入。</p>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.detail-card a {
  color: var(--primary-dark);
  font-weight: 720;
}
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
.phase-note {
  margin-top: 20px;
}
.phase-note p:last-child {
  margin-bottom: 0;
  color: var(--muted-strong);
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
