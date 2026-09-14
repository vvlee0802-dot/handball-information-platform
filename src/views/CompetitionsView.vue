<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import { competitions, getCompetitionMatches } from '@/data/handball'
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading"><div><p class="eyebrow">Competitions</p><h1>赛事</h1><p class="page-description">从赛事和赛季进入对应比赛列表。</p></div></header>
      <section class="entity-grid">
        <RouterLink v-for="item in competitions" :key="item.id" class="list-card" :to="{ name: 'competition-detail', params: { competitionId: item.id } }">
          <span class="meta-chip">{{ item.season }} · {{ item.status }}</span>
          <div><h2>{{ item.name }}</h2><p>{{ item.description }}</p></div>
          <span class="card-footer">{{ getCompetitionMatches(item.id).length }} 场比赛 →</span>
        </RouterLink>
      </section>
    </main>
  </div>
</template>
