<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { getMatch, getTeam } from '@/data/handball'

const route = useRoute()
const match = computed(() => getMatch(String(route.params.matchId)))
const isUpload = computed(() => route.name === 'match-upload')
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink v-if="match" class="back-link" :to="{ name: 'match-detail', params: { matchId: match.id } }">← 返回比赛详情</RouterLink>
      <NotFoundPanel v-if="!match" entity="比赛" />
      <section v-else class="detail-card boundary-card">
        <p class="eyebrow">Epic Boundary</p>
        <h1>{{ isUpload ? '上传录像' : '比赛分析' }}</h1>
        <p>{{ getTeam(match.teamAId)?.shortName }} vs {{ getTeam(match.teamBId)?.shortName }}</p>
        <div class="boundary-note">
          <strong>Epic 1 已完成入口衔接</strong>
          <span>{{ isUpload ? '录像上传和处理将在 Epic 2 中实现。' : '事件识别、审核和分析将在 Epic 3–4 中实现。' }}</span>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.boundary-card { max-width: 760px; }
.boundary-card h1 { margin: 0; font-size: 40px; }
.boundary-card > p:not(.eyebrow) { color: var(--muted-strong); }
.boundary-note { display: grid; gap: 6px; margin-top: 26px; padding: 20px; border-radius: 14px; color: var(--primary-dark); background: var(--primary-soft); }
.boundary-note span { color: var(--muted-strong); }
</style>
