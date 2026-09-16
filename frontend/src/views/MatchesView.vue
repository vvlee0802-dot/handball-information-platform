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
} from '@/services/matches'
import { listTeams, type TeamRecord } from '@/services/teams'
import { listVenues, type VenueRecord } from '@/services/venues'
const rows = ref<MatchRecord[]>([]),
  competitions = ref<CompetitionRecord[]>([]),
  teams = ref<TeamRecord[]>([]),
  venues = ref<VenueRecord[]>([])
const loading = ref(true),
  error = ref(''),
  saving = ref(false)
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
const cm = computed(() => new Map(competitions.value.map((x) => [x.id, x]))),
  tm = computed(() => new Map(teams.value.map((x) => [x.id, x]))),
  vm = computed(() => new Map(venues.value.map((x) => [x.id, x])))
const load = async () => {
  loading.value = true
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
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}
const submit = async () => {
  error.value = ''
  saving.value = true
  try {
    await createMatch({
      ...form,
      start_time: form.start_time.length === 5 ? `${form.start_time}:00` : form.start_time,
    })
    rows.value = await listMatches()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    saving.value = false
  }
}
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
          <p class="page-description">创建并查看数据库中的真实比赛记录。</p>
        </div>
      </header>
      <section class="panel form-panel">
        <h2 class="section-title">新增比赛</h2>
        <form @submit.prevent="submit">
          <div class="filter-grid">
            <div class="field">
              <label>赛事</label
              ><select v-model.number="form.competition_id" required>
                <option v-for="x in competitions" :key="x.id" :value="x.id">{{ x.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>主队</label
              ><select v-model.number="form.home_team_id" required>
                <option v-for="x in teams" :key="x.id" :value="x.id">{{ x.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>客队</label
              ><select v-model.number="form.away_team_id" required>
                <option v-for="x in teams" :key="x.id" :value="x.id">{{ x.name }}</option>
              </select>
            </div>
            <div class="field">
              <label>场馆</label
              ><select v-model.number="form.venue_id" required>
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
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <div class="filter-actions">
            <button class="button button-primary" :disabled="saving || teams.length < 2">
              {{ saving ? '正在保存…' : '创建比赛' }}
            </button>
          </div>
        </form>
      </section>
      <div v-if="loading" class="panel empty-state">正在加载比赛…</div>
      <div v-else-if="!rows.length" class="panel empty-state">
        暂无比赛，请先确保已有赛事、两支球队和场馆。
      </div>
      <div v-else class="table-panel">
        <table class="data-table">
          <thead>
            <tr>
              <th>比赛</th>
              <th>日期</th>
              <th>阶段</th>
              <th>比分</th>
              <th>场馆</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="x in rows" :key="x.id">
              <td>
                <RouterLink :to="{ name: 'match-detail', params: { matchId: x.id } }"
                  >{{ tm.get(x.home_team_id)?.short_name }} vs
                  {{ tm.get(x.away_team_id)?.short_name }}</RouterLink
                >
                <div>{{ cm.get(x.competition_id)?.name }}</div>
              </td>
              <td>{{ x.match_date }} {{ x.start_time.slice(0, 5) }}</td>
              <td>{{ x.stage }}</td>
              <td>{{ x.home_score ?? '—' }} : {{ x.away_score ?? '—' }}</td>
              <td>{{ vm.get(x.venue_id)?.name }}</td>
              <td>{{ matchStatusLabels[x.status] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  </div>
</template>
<style scoped>
.form-panel {
  margin-bottom: 20px;
}
.error {
  color: var(--danger);
  font-weight: 650;
}
</style>
