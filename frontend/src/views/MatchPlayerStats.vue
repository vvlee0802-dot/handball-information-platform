<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import {
  getMatchPlayerStats,
  type MatchPlayerStatsRecord,
  type PlayerMatchStatsRecord,
} from '@/services/playerStats'

const route = useRoute()
const stats = ref<MatchPlayerStatsRecord | null>(null)
const loading = ref(true)
const error = ref('')

const matchId = computed(() => Number(route.params.matchId))
const homePlayers = computed(() =>
  stats.value?.players.filter((player) => player.team_id === stats.value?.home_team_id) ?? [],
)
const awayPlayers = computed(() =>
  stats.value?.players.filter((player) => player.team_id === stats.value?.away_team_id) ?? [],
)

const teamTotals = (players: PlayerMatchStatsRecord[]) => ({
  goals: players.reduce((sum, player) => sum + player.goals, 0),
})

const load = async () => {
  if (!Number.isInteger(matchId.value) || matchId.value <= 0) {
    error.value = '比赛编号无效。'
    loading.value = false
    return
  }
  try {
    stats.value = await getMatchPlayerStats(matchId.value)
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : '球员统计加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" :to="{ name: 'match-detail', params: { matchId } }">
        ← 返回比赛详情
      </RouterLink>

      <div v-if="loading" class="detail-card empty-state">正在计算球员单场统计…</div>
      <div v-else-if="error" class="detail-card empty-state stats-error">
        <strong>统计加载失败</strong>
        <p>{{ error }}</p>
      </div>

      <template v-else-if="stats">
        <section class="stats-hero">
          <div>
            <p class="eyebrow">Player Match Statistics</p>
            <h1>{{ stats.home_team_name }} vs {{ stats.away_team_name }}</h1>
            <p>球员进球数以已确认的官方赛后统计表为准，不依赖人工视频标注。</p>
          </div>
          <div class="stats-score" aria-label="比赛比分">
            <span>{{ stats.home_score ?? '—' }}</span>
            <small>:</small>
            <span>{{ stats.away_score ?? '—' }}</span>
          </div>
        </section>

        <aside
          class="calculation-note"
          :class="{ 'calculation-note-warning': stats.goal_source === 'unavailable' }"
          role="note"
        >
          <strong>{{ stats.goal_source === 'official_report' ? '官方统计' : '暂无官方统计' }}</strong>
          <span v-if="stats.goal_source === 'official_report'">
            已读取官方赛后统计表中的球员进球数；暂不统计射门、扑救、失误、快攻和命中率。
          </span>
          <span v-else>
            请先在比赛详情上传并确认官方赛后统计表。系统不会使用人工事件代替官方数据。
          </span>
        </aside>

        <section
          v-for="team in [
            { id: stats.home_team_id, name: stats.home_team_name, players: homePlayers },
            { id: stats.away_team_id, name: stats.away_team_name, players: awayPlayers },
          ]"
          :key="team.id"
          class="team-stats"
        >
          <div class="team-heading">
            <div>
              <p class="eyebrow">Team</p>
              <h2>{{ team.name }}</h2>
            </div>
            <div class="team-summary">
              <span>进球 <strong>{{ teamTotals(team.players).goals }}</strong></span>
            </div>
          </div>

          <div class="table-panel stats-table-wrap">
            <table class="data-table stats-table">
              <thead>
                <tr>
                  <th>号码</th>
                  <th>球员</th>
                  <th>位置</th>
                  <th>进球</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="player in team.players" :key="player.player_id">
                  <td><span class="number-badge">{{ player.player_number }}</span></td>
                  <td>
                    <RouterLink
                      :to="{
                        name: 'match-player-detail',
                        params: { matchId, playerId: player.player_id },
                      }"
                    >
                      {{ player.player_name }}
                    </RouterLink>
                  </td>
                  <td>{{ player.position || '待完善' }}</td>
                  <td><strong class="goal-value">{{ player.goals }}</strong></td>
                  <td>
                    <RouterLink
                      class="player-analysis-link"
                      :to="{
                        name: 'match-player-detail',
                        params: { matchId, playerId: player.player_id },
                      }"
                    >
                      查看事件与生成集锦 →
                    </RouterLink>
                  </td>
                </tr>
                <tr v-if="team.players.length === 0">
                  <td colspan="5" class="empty-state">该队尚未录入球员。</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.stats-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  padding: 28px 30px;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--ink);
  background: white;
}
.stats-hero h1 { margin: 0; font-size: clamp(28px, 4vw, 42px); }
.stats-hero p:last-child { margin: 10px 0 0; color: var(--muted-strong); }
.stats-score { display: flex; align-items: center; gap: 14px; font-size: 42px; font-weight: 800; }
.stats-score small { color: var(--muted); font-size: 24px; }
.calculation-note { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 18px; padding: 15px 18px; border: 1px solid var(--border); border-radius: 7px; color: var(--muted-strong); background: var(--surface-soft); font-size: 13px; }
.calculation-note strong { color: var(--primary-dark); }
.calculation-note-warning { border-color: #f2d19a; background: #fff8e8; }
.calculation-note-warning strong { color: #9a5b08; }
.team-stats { margin-top: 34px; }
.team-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }
.team-heading h2 { margin: 0; font-size: 24px; }
.team-summary { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.team-summary span { padding: 7px 10px; border-radius: 5px; color: var(--muted-strong); background: var(--surface-muted); font-size: 12px; }
.team-summary strong { margin-left: 4px; color: var(--primary-dark); }
.stats-table-wrap { margin-top: 14px; overflow-x: auto; }
.stats-table { min-width: 560px; }
.goal-value { color: var(--primary-dark); font-size: 18px; }
.player-analysis-link { display: inline-flex; min-width: 150px; color: var(--primary); font-size: 13px; font-weight: 750; text-decoration: none; }
.player-analysis-link:hover { color: var(--primary-dark); text-decoration: underline; }
.number-badge { display: inline-grid; width: 32px; height: 32px; place-items: center; border-radius: 5px; color: white; background: var(--primary); font-weight: 750; }
.stats-error strong { color: var(--danger); }
.stats-error p { margin-bottom: 0; }

@media (max-width: 760px) {
  .stats-hero, .team-heading { align-items: flex-start; flex-direction: column; }
  .stats-score { font-size: 34px; }
  .team-summary { justify-content: flex-start; }
}
</style>
