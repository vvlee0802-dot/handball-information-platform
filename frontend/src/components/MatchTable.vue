<script setup lang="ts">
import { analysisStatusLabels, getCompetition, getTeam, getVenue } from '@/data/handball'
import type { Match } from '@/types/domain'

defineProps<{
  rows: Match[]
}>()

const score = (match: Match) => {
  if (match.scoreA === null || match.scoreB === null) return '—'
  return `${match.scoreA} : ${match.scoreB}`
}

const analysisClass = (match: Match) => ({
  'status-ready': match.analysisStatus === 'completed',
  'status-processing': match.analysisStatus === 'processing',
  'status-failed': match.analysisStatus === 'failed',
  'status-neutral': match.analysisStatus === 'not_started',
})
</script>

<template>
  <div v-if="rows.length" class="table-panel">
    <div class="table-meta">
      <span>共 {{ rows.length }} 场比赛</span>
      <span>点击比赛名称查看详情</span>
    </div>
    <table class="data-table">
      <thead>
        <tr>
          <th>比赛</th>
          <th>日期与时间</th>
          <th>阶段</th>
          <th>比分</th>
          <th>场馆</th>
          <th>分析状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="match in rows" :key="match.id">
          <td>
            <RouterLink :to="{ name: 'match-detail', params: { matchId: match.id } }">
              {{ getTeam(match.teamAId)?.shortName }} vs {{ getTeam(match.teamBId)?.shortName }}
            </RouterLink>
            <div class="subtext">{{ getCompetition(match.competitionId)?.name }}</div>
          </td>
          <td>{{ match.date }}<div class="subtext">{{ match.startTime }}</div></td>
          <td>{{ match.stage }}</td>
          <td class="score">{{ score(match) }}</td>
          <td>
            <RouterLink :to="{ name: 'venue-detail', params: { venueId: match.venueId } }">
              {{ getVenue(match.venueId)?.name }}
            </RouterLink>
          </td>
          <td><span class="status-badge" :class="analysisClass(match)">{{ analysisStatusLabels[match.analysisStatus] }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="panel empty-state">没有符合当前条件的比赛，请调整或清除筛选条件。</div>
</template>

<style scoped>
.subtext { margin-top: 3px; color: var(--muted); font-size: 12px; }
.score { font-size: 17px; font-weight: 780; white-space: nowrap; }
</style>
