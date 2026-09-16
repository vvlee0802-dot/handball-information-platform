<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
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
onMounted(load)
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
            <button v-if="!editing" class="button button-secondary" @click="startEdit">
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
@media (max-width: 620px) {
  .detail-actions {
    align-items: flex-start;
  }
}
</style>
