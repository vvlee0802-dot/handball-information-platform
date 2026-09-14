<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import MatchTable from '@/components/MatchTable.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { getTeam, getTeamMatches, getTeamPlayers } from '@/data/handball'

const route = useRoute()
const team = computed(() => getTeam(String(route.params.teamId)))
const roster = computed(() => team.value ? getTeamPlayers(team.value.id) : [])
const relatedMatches = computed(() => team.value ? getTeamMatches(team.value.id) : [])
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/teams">← 返回球队列表</RouterLink>
      <NotFoundPanel v-if="!team" entity="球队" />
      <template v-else>
        <section class="detail-card"><div class="detail-header"><div><p class="eyebrow">Team</p><h1 class="detail-title">{{ team.name }}</h1><p class="page-description">{{ team.description }}</p></div><span class="meta-chip">{{ team.gender }}</span></div><dl class="info-list"><div><dt>国家或地区</dt><dd>{{ team.country }}</dd></div><div><dt>所在城市</dt><dd>{{ team.city }}</dd></div></dl></section>
        <section class="linked-section"><h2 class="section-title">球队阵容</h2><div class="table-panel"><table class="data-table"><thead><tr><th>号码</th><th>球员</th><th>位置</th><th>出生日期</th></tr></thead><tbody><tr v-for="player in roster" :key="player.id"><td>#{{ player.number }}</td><td><RouterLink :to="{ name: 'player-detail', params: { playerId: player.id } }">{{ player.name }}</RouterLink></td><td>{{ player.position }}</td><td>{{ player.birthDate }}</td></tr></tbody></table></div></section>
        <section class="linked-section"><div class="page-heading"><div><h2 class="section-title">相关比赛</h2><p class="page-description">该球队参与的比赛。</p></div><RouterLink class="button button-secondary" :to="{ name: 'matches', query: { team: team.id } }">在比赛页筛选</RouterLink></div><MatchTable :rows="relatedMatches" /></section>
      </template>
    </main>
  </div>
</template>
