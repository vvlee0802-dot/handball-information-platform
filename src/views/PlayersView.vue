<script setup lang="ts">
import { computed, ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { getTeam, players, teams } from '@/data/handball'

const keyword = ref('')
const teamId = ref('')
const visiblePlayers = computed(() => players.filter((player) => {
  const team = getTeam(player.teamId)
  const q = keyword.value.trim().toLocaleLowerCase('zh-CN')
  return (!q || `${player.name} ${player.position} ${team?.name}`.toLocaleLowerCase('zh-CN').includes(q)) && (!teamId.value || player.teamId === teamId.value)
}))
const clear = () => { keyword.value = ''; teamId.value = '' }
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading"><div><p class="eyebrow">Players</p><h1>球员</h1><p class="page-description">查看球员基础资料和所属球队。个人比赛分析属于 Phase 2。</p></div></header>
      <section class="panel"><div class="filter-grid"><div class="field"><label for="player-keyword">球员名称或位置</label><input id="player-keyword" v-model="keyword" type="search" placeholder="输入姓名或位置" /></div><div class="field"><label for="player-team">所属球队</label><select id="player-team" v-model="teamId"><option value="">全部球队</option><option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option></select></div></div><div class="filter-actions"><button class="button button-secondary" @click="clear">清除筛选</button></div></section>
      <section v-if="visiblePlayers.length" class="entity-grid player-grid">
        <RouterLink v-for="player in visiblePlayers" :key="player.id" class="list-card" :to="{ name: 'player-detail', params: { playerId: player.id } }"><span class="meta-chip">#{{ player.number }} · {{ player.position }}</span><div><h2>{{ player.name }}</h2><p>{{ getTeam(player.teamId)?.name }}</p></div><span class="card-footer">查看球员资料 →</span></RouterLink>
      </section>
      <div v-else class="panel empty-state">没有符合当前条件的球员。</div>
    </main>
  </div>
</template>

<style scoped>.player-grid { margin-top: 20px; }</style>
