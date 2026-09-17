<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { createPlayer, listPlayers, type PlayerInput, type PlayerRecord } from '@/services/players'
import { listTeams, type TeamRecord } from '@/services/teams'

const authStore = useAuthStore()
const players = ref<PlayerRecord[]>([])
const teams = ref<TeamRecord[]>([])
const keyword = ref('')
const teamFilter = ref('')
const isLoading = ref(true)
const errorMessage = ref('')
const isSubmitting = ref(false)
const formError = ref('')
const form = reactive<PlayerInput>({
  name: '',
  number: 0,
  position: '',
  team_id: 0,
  birth_date: '',
  description: '',
})

const teamMap = computed(() => new Map(teams.value.map((team) => [team.id, team])))
const visiblePlayers = computed(() => {
  const query = keyword.value.trim().toLocaleLowerCase('zh-CN')
  return players.value.filter((player) => {
    const team = teamMap.value.get(player.team_id)
    const searchable = `${player.name} ${player.position} ${team?.name ?? ''}`.toLocaleLowerCase(
      'zh-CN',
    )
    return (
      (!query || searchable.includes(query)) &&
      (!teamFilter.value || player.team_id === Number(teamFilter.value))
    )
  })
})

const loadData = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [playerRows, teamRows] = await Promise.all([listPlayers(), listTeams()])
    players.value = playerRows
    teams.value = teamRows
    if (!form.team_id && teamRows[0]) form.team_id = teamRows[0].id
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '球员数据加载失败'
  } finally {
    isLoading.value = false
  }
}

const handleCreate = async () => {
  formError.value = ''
  isSubmitting.value = true
  try {
    await createPlayer({ ...form, description: form.description || null })
    Object.assign(form, {
      name: '',
      number: 0,
      position: '',
      team_id: teams.value[0]?.id ?? 0,
      birth_date: '',
      description: '',
    })
    players.value = await listPlayers()
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '球员创建失败'
  } finally {
    isSubmitting.value = false
  }
}

const clearFilters = () => {
  keyword.value = ''
  teamFilter.value = ''
}
onMounted(loadData)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Players</p>
          <h1>球员</h1>
          <p class="page-description">维护球员资料及其所属球队。</p>
        </div>
      </header>

      <section v-if="authStore.hasPermission('manage_competition_data')" class="panel player-form-panel">
        <h2 class="section-title">新增球员</h2>
        <div v-if="!isLoading && teams.length === 0" class="empty-state">
          请先在球队页面创建至少一支球队。
        </div>
        <form v-else @submit.prevent="handleCreate">
          <div class="filter-grid">
            <div class="field">
              <label for="player-name">球员姓名</label
              ><input id="player-name" v-model="form.name" required maxlength="120" />
            </div>
            <div class="field">
              <label for="player-number">号码</label
              ><input
                id="player-number"
                v-model.number="form.number"
                type="number"
                required
                min="0"
                max="99"
              />
            </div>
            <div class="field">
              <label for="player-position">位置</label
              ><input id="player-position" v-model="form.position" required maxlength="50" />
            </div>
            <div class="field">
              <label for="player-team">所属球队</label
              ><select id="player-team" v-model.number="form.team_id" required>
                <option v-for="team in teams" :key="team.id" :value="team.id">
                  {{ team.name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label for="player-birth-date">出生日期</label
              ><input id="player-birth-date" v-model="form.birth_date" type="date" required />
            </div>
            <div class="field field-wide">
              <label for="player-description">简介</label
              ><input id="player-description" v-model="form.description" maxlength="500" />
            </div>
          </div>
          <p v-if="formError" class="form-message form-message-error">创建失败：{{ formError }}</p>
          <div class="filter-actions">
            <button
              class="button button-primary"
              type="submit"
              :disabled="isSubmitting || teams.length === 0"
            >
              {{ isSubmitting ? '正在保存…' : '创建球员' }}
            </button>
          </div>
        </form>
      </section>

      <section class="panel filter-panel">
        <div class="filter-grid">
          <div class="field">
            <label for="player-keyword">球员名称或位置</label
            ><input
              id="player-keyword"
              v-model="keyword"
              type="search"
              placeholder="输入姓名或位置"
            />
          </div>
          <div class="field">
            <label for="player-team-filter">所属球队</label
            ><select id="player-team-filter" v-model="teamFilter">
              <option value="">全部球队</option>
              <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
            </select>
          </div>
        </div>
        <div class="filter-actions">
          <button class="button button-secondary" type="button" @click="clearFilters">
            清除筛选
          </button>
        </div>
      </section>

      <div v-if="isLoading" class="panel empty-state">正在从后端加载球员…</div>
      <div v-else-if="errorMessage" class="panel empty-state">
        <p>无法加载球员：{{ errorMessage }}</p>
        <button class="button button-secondary" type="button" @click="loadData">重新加载</button>
      </div>
      <section v-else-if="visiblePlayers.length" class="entity-grid player-grid">
        <RouterLink
          v-for="player in visiblePlayers"
          :key="player.id"
          class="list-card"
          :to="{ name: 'player-detail', params: { playerId: player.id } }"
        >
          <span class="meta-chip">#{{ player.number }} · {{ player.position }}</span>
          <div>
            <h2>{{ player.name }}</h2>
            <p>{{ teamMap.get(player.team_id)?.name || '未知球队' }}</p>
          </div>
          <span class="card-footer">查看球员资料 →</span>
        </RouterLink>
      </section>
      <div v-else class="panel empty-state">没有符合当前条件的球员。</div>
    </main>
  </div>
</template>

<style scoped>
.player-form-panel {
  margin-bottom: 20px;
}
.filter-panel {
  margin-bottom: 20px;
}
.player-grid {
  margin-top: 20px;
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
@media (max-width: 900px) {
  .field-wide {
    grid-column: span 1;
  }
}
</style>
