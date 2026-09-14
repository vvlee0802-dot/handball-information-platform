<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import MatchTable from '@/components/MatchTable.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { getVenue, getVenueMatches } from '@/data/handball'

const route = useRoute()
const venue = computed(() => getVenue(String(route.params.venueId)))
const relatedMatches = computed(() => venue.value ? getVenueMatches(venue.value.id) : [])
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/venues">← 返回场馆列表</RouterLink>
      <NotFoundPanel v-if="!venue" entity="场馆" />
      <template v-else>
        <section class="detail-card"><div class="detail-header"><div><p class="eyebrow">Venue</p><h1 class="detail-title">{{ venue.name }}</h1><p class="page-description">{{ venue.description }}</p></div><span class="meta-chip">{{ venue.city }}</span></div><dl class="info-list"><div><dt>地址</dt><dd>{{ venue.address }}</dd></div><div><dt>容量</dt><dd>{{ venue.capacity.toLocaleString('zh-CN') }} 人</dd></div></dl></section>
        <section class="linked-section"><div class="page-heading"><div><h2 class="section-title">场馆比赛</h2><p class="page-description">在该场馆举办的比赛。</p></div><RouterLink class="button button-secondary" :to="{ name: 'matches', query: { venue: venue.id } }">在比赛页筛选</RouterLink></div><MatchTable :rows="relatedMatches" /></section>
      </template>
    </main>
  </div>
</template>
