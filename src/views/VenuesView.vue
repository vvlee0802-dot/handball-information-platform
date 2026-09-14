<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import { getVenueMatches, venues } from '@/data/handball'
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading"><div><p class="eyebrow">Venues</p><h1>场馆</h1><p class="page-description">浏览比赛场馆并查看在该场馆举办的比赛。</p></div></header>
      <section class="entity-grid"><RouterLink v-for="venue in venues" :key="venue.id" class="list-card" :to="{ name: 'venue-detail', params: { venueId: venue.id } }"><span class="meta-chip">{{ venue.city }}</span><div><h2>{{ venue.name }}</h2><p>{{ venue.address }}</p></div><span class="card-footer">{{ getVenueMatches(venue.id).length }} 场比赛 →</span></RouterLink></section>
    </main>
  </div>
</template>
