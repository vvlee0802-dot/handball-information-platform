<script setup lang="ts">
import { computed } from 'vue'
import { matchStatusLabels, type MatchRecord } from '@/services/matches'
import type { CompetitionRecord } from '@/services/competitions'
import type { TeamRecord } from '@/services/teams'
import type { VenueRecord } from '@/services/venues'

const props = defineProps<{
  rows: MatchRecord[]
  competitions: CompetitionRecord[]
  teams: TeamRecord[]
  venues: VenueRecord[]
}>()
const competitionsById = computed(() => new Map(props.competitions.map((x) => [x.id, x])))
const teamsById = computed(() => new Map(props.teams.map((x) => [x.id, x])))
const venuesById = computed(() => new Map(props.venues.map((x) => [x.id, x])))
</script>
<template>
  <div v-if="rows.length" class="table-panel">
    <div class="table-meta">共 {{ rows.length }} 场比赛</div>
    <table class="data-table">
      <thead>
        <tr>
          <th>比赛</th>
          <th>日期与时间</th>
          <th>阶段</th>
          <th>比分</th>
          <th>场馆</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td>
            <RouterLink :to="{ name: 'match-detail', params: { matchId: row.id } }"
              >{{ teamsById.get(row.home_team_id)?.short_name }} vs
              {{ teamsById.get(row.away_team_id)?.short_name }}</RouterLink
            >
            <div class="subtext">{{ competitionsById.get(row.competition_id)?.name }}</div>
          </td>
          <td>
            {{ row.match_date }}
            <div class="subtext">{{ row.start_time.slice(0, 5) }}</div>
          </td>
          <td>{{ row.stage }}</td>
          <td class="score">{{ row.home_score ?? '—' }} : {{ row.away_score ?? '—' }}</td>
          <td>{{ venuesById.get(row.venue_id)?.name }}</td>
          <td>{{ matchStatusLabels[row.status] }}</td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="panel empty-state">暂无关联比赛。</div>
</template>
<style scoped>
.subtext {
  margin-top: 3px;
  color: var(--muted);
  font-size: 12px;
}
.score {
  font-weight: 780;
  white-space: nowrap;
}
</style>
