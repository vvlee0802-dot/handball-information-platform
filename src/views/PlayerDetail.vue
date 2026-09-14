<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { getPlayer, getTeam } from '@/data/handball'

const route = useRoute()
const player = computed(() => getPlayer(String(route.params.playerId)))
const team = computed(() => player.value ? getTeam(player.value.teamId) : undefined)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/players">← 返回球员列表</RouterLink>
      <NotFoundPanel v-if="!player" entity="球员" />
      <template v-else>
        <section class="detail-card"><div class="detail-header"><div><p class="eyebrow">Player</p><h1 class="detail-title">{{ player.name }}</h1><p class="page-description">{{ player.description }}</p></div><span class="meta-chip">#{{ player.number }}</span></div><dl class="info-list"><div><dt>位置</dt><dd>{{ player.position }}</dd></div><div><dt>出生日期</dt><dd>{{ player.birthDate }}</dd></div><div><dt>所属球队</dt><dd><RouterLink :to="{ name: 'team-detail', params: { teamId: player.teamId } }">{{ team?.name }} →</RouterLink></dd></div><div><dt>球队所在城市</dt><dd>{{ team?.city }}</dd></div></dl></section>
        <section class="detail-card phase-note"><p class="eyebrow">Phase 2</p><h2 class="section-title">个人比赛分析</h2><p>进球、射门、扑救、失误、快攻等个人统计及对应事件视频将在 Phase 2 接入，不属于当前 Epic 1 的验收范围。</p></section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.detail-card a { color: var(--primary-dark); font-weight: 720; }
.phase-note { margin-top: 20px; }
.phase-note p:last-child { margin-bottom: 0; color: var(--muted-strong); }
</style>
