<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import { listCompetitions, type CompetitionRecord } from '@/services/competitions'
import {
  createMatch,
  listMatches,
  matchStatusLabels,
  type MatchInput,
  type MatchRecord,
  type MatchStatus,
} from '@/services/matches'
import { listTeams, type TeamRecord } from '@/services/teams'
import { listVenues, type VenueRecord } from '@/services/venues'
import { useAuthStore } from '@/stores/auth'

type MatchFilters = {
  keyword: string
  competition_id: string
  team_id: string
  status: '' | MatchStatus
  date_from: string
  date_to: string
  stage: string
  venue_id: string
}

const emptyFilters = (): MatchFilters => ({
  keyword: '',
  competition_id: '',
  team_id: '',
  status: '',
  date_from: '',
  date_to: '',
  stage: '',
  venue_id: '',
})

const authStore = useAuthStore()
const rows = ref<MatchRecord[]>([])
const competitions = ref<CompetitionRecord[]>([])
const teams = ref<TeamRecord[]>([])
const venues = ref<VenueRecord[]>([])
const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const formError = ref('')
const showCreateModal = ref(false)
const showAdvancedFilters = ref(false)
const filterForm = reactive<MatchFilters>(emptyFilters())
const appliedFilters = reactive<MatchFilters>(emptyFilters())

const form = reactive<MatchInput>({
  competition_id: 0,
  home_team_id: 0,
  away_team_id: 0,
  venue_id: 0,
  match_date: '',
  start_time: '19:30',
  stage: '小组赛',
  status: 'scheduled',
  home_score: null,
  away_score: null,
})

const competitionMap = computed(() => new Map(competitions.value.map((item) => [item.id, item])))
const teamMap = computed(() => new Map(teams.value.map((item) => [item.id, item])))
const venueMap = computed(() => new Map(venues.value.map((item) => [item.id, item])))
const activeFilterCount = computed(() => Object.values(appliedFilters).filter(Boolean).length)
const filteredRows = computed(() => {
  const keyword = appliedFilters.keyword.trim().toLocaleLowerCase('zh-CN')

  return [...rows.value]
    .filter((match) => {
      const searchable = [
        competitionMap.value.get(match.competition_id)?.name,
        teamMap.value.get(match.home_team_id)?.name,
        teamMap.value.get(match.away_team_id)?.name,
        venueMap.value.get(match.venue_id)?.name,
        match.stage,
      ]
        .filter(Boolean)
        .join(' ')
        .toLocaleLowerCase('zh-CN')

      return (
        (!keyword || searchable.includes(keyword)) &&
        (!appliedFilters.competition_id ||
          match.competition_id === Number(appliedFilters.competition_id)) &&
        (!appliedFilters.team_id ||
          match.home_team_id === Number(appliedFilters.team_id) ||
          match.away_team_id === Number(appliedFilters.team_id)) &&
        (!appliedFilters.status || match.status === appliedFilters.status) &&
        (!appliedFilters.date_from || match.match_date >= appliedFilters.date_from) &&
        (!appliedFilters.date_to || match.match_date <= appliedFilters.date_to) &&
        (!appliedFilters.stage ||
          match.stage.toLocaleLowerCase('zh-CN').includes(
            appliedFilters.stage.trim().toLocaleLowerCase('zh-CN'),
          )) &&
        (!appliedFilters.venue_id || match.venue_id === Number(appliedFilters.venue_id))
      )
    })
    .sort((left, right) =>
      `${right.match_date} ${right.start_time}`.localeCompare(`${left.match_date} ${left.start_time}`),
    )
})

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    ;[rows.value, competitions.value, teams.value, venues.value] = await Promise.all([
      listMatches(),
      listCompetitions(),
      listTeams(),
      listVenues(),
    ])
    form.competition_id ||= competitions.value[0]?.id ?? 0
    form.home_team_id ||= teams.value[0]?.id ?? 0
    form.away_team_id ||= teams.value[1]?.id ?? 0
    form.venue_id ||= venues.value[0]?.id ?? 0
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '比赛数据加载失败'
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  formError.value = ''
  showCreateModal.value = true
}

const closeCreateModal = () => {
  if (!saving.value) showCreateModal.value = false
}

const submit = async () => {
  formError.value = ''
  if (form.home_team_id === form.away_team_id) {
    formError.value = '队伍 1 和队伍 2 不能相同。'
    return
  }

  saving.value = true
  try {
    await createMatch({
      ...form,
      start_time: form.start_time.length === 5 ? `${form.start_time}:00` : form.start_time,
    })
    rows.value = await listMatches()
    showCreateModal.value = false
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '比赛创建失败'
  } finally {
    saving.value = false
  }
}

const applyFilters = () => Object.assign(appliedFilters, filterForm)
const resetFilters = () => {
  Object.assign(filterForm, emptyFilters())
  Object.assign(appliedFilters, emptyFilters())
  showAdvancedFilters.value = false
}

const statusClass = (status: MatchStatus) => ({
  'status-ready': status === 'completed',
  'status-processing': status === 'live',
  'status-failed': status === 'cancelled',
  'status-neutral': status === 'scheduled',
})

onMounted(load)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Matches</p>
          <h1>比赛</h1>
          <p class="page-description">搜索比赛记录，并进入详情页查看视频、事件和分析结果。</p>
        </div>
        <button
          v-if="authStore.hasPermission('manage_competition_data')"
          class="button button-primary"
          type="button"
          @click="openCreateModal"
        >
          新增比赛
        </button>
      </header>

      <section class="panel search-panel" aria-labelledby="match-search-title">
        <div class="search-heading">
          <div>
            <h2 id="match-search-title" class="section-title">搜索比赛</h2>
            <p>可按赛事、参赛球队、日期和状态筛选比赛。</p>
          </div>
          <span v-if="activeFilterCount" class="meta-chip">已应用 {{ activeFilterCount }} 项条件</span>
        </div>

        <form @submit.prevent="applyFilters">
          <div class="filter-grid match-filter-grid">
            <div class="field field-keyword">
              <label for="match-keyword">关键词</label>
              <input
                id="match-keyword"
                v-model="filterForm.keyword"
                type="search"
                placeholder="搜索赛事、球队、阶段或场馆"
              />
            </div>
            <div class="field">
              <label for="match-team">参赛球队</label>
              <select id="match-team" v-model="filterForm.team_id">
                <option value="">全部球队</option>
                <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
              </select>
            </div>
            <div class="field">
              <label for="match-competition">所属赛事</label>
              <select id="match-competition" v-model="filterForm.competition_id">
                <option value="">全部赛事</option>
                <option v-for="competition in competitions" :key="competition.id" :value="competition.id">
                  {{ competition.name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label for="match-date-from">开始日期</label>
              <input id="match-date-from" v-model="filterForm.date_from" type="date" />
            </div>
            <div class="field">
              <label for="match-date-to">结束日期</label>
              <input id="match-date-to" v-model="filterForm.date_to" type="date" />
            </div>
            <div class="field">
              <label for="match-status">比赛状态</label>
              <select id="match-status" v-model="filterForm.status">
                <option value="">全部状态</option>
                <option value="scheduled">未开始</option>
                <option value="live">进行中</option>
                <option value="completed">已结束</option>
                <option value="cancelled">已取消</option>
              </select>
            </div>
          </div>

          <div v-if="showAdvancedFilters" class="filter-grid advanced-filters">
            <div class="field">
              <label for="match-stage">比赛阶段</label>
              <input id="match-stage" v-model="filterForm.stage" placeholder="例如：小组赛、决赛" />
            </div>
            <div class="field">
              <label for="match-venue">场馆</label>
              <select id="match-venue" v-model="filterForm.venue_id">
                <option value="">全部场馆</option>
                <option v-for="venue in venues" :key="venue.id" :value="venue.id">{{ venue.name }}</option>
              </select>
            </div>
          </div>

          <div class="filter-actions search-actions">
            <button
              class="button button-secondary advanced-toggle"
              type="button"
              @click="showAdvancedFilters = !showAdvancedFilters"
            >
              {{ showAdvancedFilters ? '收起筛选' : '更多筛选' }}
            </button>
            <span class="action-spacer"></span>
            <button class="button button-secondary" type="button" @click="resetFilters">重置</button>
            <button class="button button-primary" type="submit">搜索比赛</button>
          </div>
        </form>
      </section>

      <div v-if="loading" class="panel empty-state result-state">正在加载比赛…</div>
      <div v-else-if="loadError" class="panel empty-state result-state">
        <p>无法加载比赛：{{ loadError }}</p>
        <button class="button button-secondary" type="button" @click="load">重新加载</button>
      </div>
      <div v-else-if="filteredRows.length === 0" class="panel empty-state result-state">
        <p>{{ rows.length ? '没有符合当前条件的比赛。' : '数据库中还没有比赛。' }}</p>
        <button v-if="activeFilterCount" class="button button-secondary" type="button" @click="resetFilters">
          清除筛选
        </button>
      </div>
      <div v-else class="table-panel match-table-panel">
        <div class="table-meta">
          <span>共找到 {{ filteredRows.length }} 场比赛</span>
          <span>按比赛日期从近到远排列</span>
        </div>
        <table class="data-table match-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>赛事</th>
              <th>对阵</th>
              <th>比分</th>
              <th>阶段</th>
              <th>场馆</th>
              <th>状态</th>
              <th aria-label="操作"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="match in filteredRows" :key="match.id">
              <td class="date-cell">
                <strong>{{ match.match_date }}</strong>
                <span>{{ match.start_time.slice(0, 5) }}</span>
              </td>
              <td>{{ competitionMap.get(match.competition_id)?.name || '未知赛事' }}</td>
              <td class="versus-cell">
                <strong>{{ teamMap.get(match.home_team_id)?.name || '未知球队' }}</strong>
                <span>vs</span>
                <strong>{{ teamMap.get(match.away_team_id)?.name || '未知球队' }}</strong>
              </td>
              <td class="score-cell">{{ match.home_score ?? '—' }} : {{ match.away_score ?? '—' }}</td>
              <td>{{ match.stage }}</td>
              <td>{{ venueMap.get(match.venue_id)?.name || '未设置' }}</td>
              <td>
                <span class="status-badge" :class="statusClass(match.status)">
                  {{ matchStatusLabels[match.status] }}
                </span>
              </td>
              <td class="action-cell">
                <RouterLink :to="{ name: 'match-detail', params: { matchId: match.id } }">
                  查看详情 →
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <div
      v-if="showCreateModal"
      class="modal-overlay"
      role="presentation"
      tabindex="-1"
      @click.self="closeCreateModal"
      @keydown.esc="closeCreateModal"
    >
        <section class="create-dialog" role="dialog" aria-modal="true" aria-labelledby="create-match-title">
          <header class="dialog-heading">
            <div>
              <p class="eyebrow">Create match</p>
              <h2 id="create-match-title">新增比赛</h2>
              <p>填写比赛的基础信息，创建后可继续上传视频和录入事件。</p>
            </div>
            <button class="dialog-close" type="button" aria-label="关闭新增比赛窗口" @click="closeCreateModal">×</button>
          </header>

          <div v-if="!loading && (competitions.length === 0 || teams.length < 2 || venues.length === 0)" class="dialog-notice">
            创建比赛前，请先准备至少一项赛事、两支球队和一个场馆。
          </div>

          <form @submit.prevent="submit">
            <div class="filter-grid create-grid">
              <div class="field field-wide">
                <label for="create-match-competition">赛事</label>
                <select id="create-match-competition" v-model.number="form.competition_id" required>
                  <option v-for="competition in competitions" :key="competition.id" :value="competition.id">
                    {{ competition.name }}
                  </option>
                </select>
              </div>
              <div class="field">
                <label for="create-match-team-one">队伍 1</label>
                <select id="create-match-team-one" v-model.number="form.home_team_id" required>
                  <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
                </select>
              </div>
              <div class="field">
                <label for="create-match-team-two">队伍 2</label>
                <select id="create-match-team-two" v-model.number="form.away_team_id" required>
                  <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
                </select>
              </div>
              <div class="field field-wide">
                <label for="create-match-venue">场馆</label>
                <select id="create-match-venue" v-model.number="form.venue_id" required>
                  <option v-for="venue in venues" :key="venue.id" :value="venue.id">{{ venue.name }}</option>
                </select>
              </div>
              <div class="field">
                <label for="create-match-date">日期</label>
                <input id="create-match-date" v-model="form.match_date" type="date" required />
              </div>
              <div class="field">
                <label for="create-match-time">时间</label>
                <input id="create-match-time" v-model="form.start_time" type="time" required />
              </div>
              <div class="field field-wide">
                <label for="create-match-stage">阶段</label>
                <input id="create-match-stage" v-model="form.stage" required maxlength="80" />
              </div>
            </div>
            <p v-if="formError" class="form-message form-message-error">{{ formError }}</p>
            <div class="filter-actions dialog-actions">
              <button class="button button-secondary" type="button" @click="closeCreateModal">取消</button>
              <button
                class="button button-primary"
                type="submit"
                :disabled="saving || teams.length < 2 || form.home_team_id === form.away_team_id"
              >
                {{ saving ? '正在保存…' : '创建比赛' }}
              </button>
            </div>
          </form>
        </section>
    </div>
  </div>
</template>

<style scoped>
.search-panel { margin-bottom: 20px; }
.search-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.search-heading .section-title { margin-bottom: 3px; }
.search-heading p { margin: 0; color: var(--muted-strong); font-size: 13px; }
.field-keyword { grid-column: span 2; }
.advanced-filters { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); }
.search-actions { align-items: center; }
.action-spacer { flex: 1; }
.result-state { margin-top: 20px; }
.result-state p { margin: 0 0 14px; }
.match-table-panel { margin-top: 0; }
.match-table { min-width: 1120px; }
.date-cell { display: grid; gap: 1px; white-space: nowrap; }
.date-cell span { color: var(--muted); font-size: 12px; }
.versus-cell { min-width: 210px; }
.versus-cell strong { display: block; }
.versus-cell span { color: var(--muted); font-size: 11px; text-transform: uppercase; }
.score-cell { color: var(--primary-dark); font-size: 16px; font-weight: 800; white-space: nowrap; }
.action-cell { text-align: right; white-space: nowrap; }

.modal-overlay { position: fixed; z-index: 200; inset: 0; display: grid; padding: 24px; place-items: center; overflow-y: auto; background: rgb(7 18 34 / 72%); backdrop-filter: blur(5px); }
.create-dialog { width: min(760px, 100%); max-height: calc(100vh - 48px); padding: 26px; overflow-y: auto; border-radius: 22px; background: white; box-shadow: 0 30px 90px rgb(5 18 38 / 35%); }
.dialog-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 22px; }
.dialog-heading h2 { margin: 0; font-size: 25px; }
.dialog-heading p:last-child { margin: 6px 0 0; color: var(--muted-strong); }
.dialog-close { display: grid; width: 38px; height: 38px; flex: 0 0 auto; place-items: center; border-radius: 50%; color: var(--muted-strong); background: var(--surface-soft); cursor: pointer; font-size: 25px; line-height: 1; }
.dialog-close:hover { color: var(--ink); background: var(--surface-muted); }
.create-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.create-grid .field-wide { grid-column: span 2; }
.dialog-notice { margin-bottom: 18px; padding: 13px 15px; border-radius: 12px; color: var(--warning); background: var(--warning-soft); }
.dialog-actions { margin-top: 22px; }
.form-message { margin: 16px 0 0; font-weight: 650; }
.form-message-error { color: var(--danger); }

@media (max-width: 900px) {
  .field-keyword { grid-column: span 2; }
  .match-table-panel { overflow-x: auto; }
}

@media (max-width: 620px) {
  .field-keyword { grid-column: span 1; }
  .search-heading { flex-direction: column; }
  .search-actions { align-items: stretch; flex-direction: column; }
  .search-actions .button { width: 100%; }
  .action-spacer { display: none; }
  .modal-overlay { padding: 10px; place-items: start center; }
  .create-dialog { max-height: none; padding: 20px; border-radius: 18px; }
  .create-grid { grid-template-columns: 1fr; }
  .create-grid .field-wide { grid-column: span 1; }
  .dialog-heading p:last-child { font-size: 13px; }
}
</style>
