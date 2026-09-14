<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import { getTeamMatches, getTeamPlayers, teams } from '@/data/handball'
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading"><div><p class="eyebrow">Teams</p><h1>球队</h1><p class="page-description">查看球队资料、阵容和参与的比赛。</p></div></header>
      <section class="entity-grid">
        <RouterLink v-for="team in teams" :key="team.id" class="list-card" :to="{ name: 'team-detail', params: { teamId: team.id } }">
          <span class="meta-chip">{{ team.gender }} · {{ team.country }}</span>
          <div><h2>{{ team.name }}</h2><p>{{ team.description }}</p></div>
          <span class="card-footer">{{ getTeamPlayers(team.id).length }} 名球员 · {{ getTeamMatches(team.id).length }} 场比赛 →</span>
        </RouterLink>
      </section>
    </main>
  </div>
</template>
