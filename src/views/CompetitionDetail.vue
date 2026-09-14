<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import MatchTable from '@/components/MatchTable.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { getCompetition, getCompetitionMatches } from '@/data/handball'

const route = useRoute()
const competition = computed(() => getCompetition(String(route.params.competitionId)))
const relatedMatches = computed(() => competition.value ? getCompetitionMatches(competition.value.id) : [])
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/competitions">← 返回赛事列表</RouterLink>
      <NotFoundPanel v-if="!competition" entity="赛事" />
      <template v-else>
        <section class="detail-card">
          <div class="detail-header"><div><p class="eyebrow">Competition</p><h1 class="detail-title">{{ competition.name }}</h1><p class="page-description">{{ competition.description }}</p></div><span class="status-badge status-neutral">{{ competition.status }}</span></div>
          <dl class="info-list"><div><dt>赛季</dt><dd>{{ competition.season }}</dd></div><div><dt>赛事级别</dt><dd>{{ competition.stage }}</dd></div></dl>
        </section>
        <section class="linked-section"><div class="page-heading"><div><h2 class="section-title">赛事比赛</h2><p class="page-description">该赛事下的全部比赛。</p></div><RouterLink class="button button-secondary" :to="{ name: 'matches', query: { competition: competition.id } }">在比赛页筛选</RouterLink></div><MatchTable :rows="relatedMatches" /></section>
      </template>
    </main>
  </div>
</template>
