<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import MatchTable from '@/components/MatchTable.vue'
import { competitions, filterMatches, matches, teams, venues } from '@/data/handball'
import type { MatchFilters, MatchStatus } from '@/types/domain'

const route = useRoute()
const emptyFilters = (): MatchFilters => ({ keyword: '', competitionId: '', teamId: '', venueId: '', stage: '', status: '', date: '' })
const filters = reactive<MatchFilters>(emptyFilters())
const stages = [...new Set(matches.map((match) => match.stage))]

const applyQuery = () => {
  Object.assign(filters, emptyFilters(), {
    competitionId: typeof route.query.competition === 'string' ? route.query.competition : '',
    teamId: typeof route.query.team === 'string' ? route.query.team : '',
    venueId: typeof route.query.venue === 'string' ? route.query.venue : '',
    stage: typeof route.query.stage === 'string' ? route.query.stage : '',
    status: typeof route.query.status === 'string' ? route.query.status as MatchStatus : '',
  })
}

watch(() => route.query, applyQuery, { immediate: true })
const filteredMatches = computed(() => filterMatches(matches, filters))
const clearFilters = () => Object.assign(filters, emptyFilters())
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Matches</p>
          <h1>比赛</h1>
          <p class="page-description">按赛事、球队、场馆、日期、阶段或状态快速定位需要复盘的比赛。</p>
        </div>
      </header>

      <section class="panel" aria-label="比赛筛选">
        <div class="filter-grid">
          <div class="field wide-field">
            <label for="keyword">名称或地点</label>
            <input id="keyword" v-model="filters.keyword" type="search" placeholder="输入球队、赛事、场馆或阶段" />
          </div>
          <div class="field">
            <label for="competition">赛事</label>
            <select id="competition" v-model="filters.competitionId"><option value="">全部赛事</option><option v-for="item in competitions" :key="item.id" :value="item.id">{{ item.name }}</option></select>
          </div>
          <div class="field">
            <label for="team">球队</label>
            <select id="team" v-model="filters.teamId"><option value="">全部球队</option><option v-for="item in teams" :key="item.id" :value="item.id">{{ item.shortName }}</option></select>
          </div>
          <div class="field">
            <label for="venue">场馆</label>
            <select id="venue" v-model="filters.venueId"><option value="">全部场馆</option><option v-for="item in venues" :key="item.id" :value="item.id">{{ item.name }}</option></select>
          </div>
          <div class="field">
            <label for="date">比赛日期</label>
            <input id="date" v-model="filters.date" type="date" />
          </div>
          <div class="field">
            <label for="stage">比赛阶段</label>
            <select id="stage" v-model="filters.stage"><option value="">全部阶段</option><option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option></select>
          </div>
          <div class="field">
            <label for="status">比赛状态</label>
            <select id="status" v-model="filters.status"><option value="">全部状态</option><option value="未开始">未开始</option><option value="进行中">进行中</option><option value="已结束">已结束</option></select>
          </div>
        </div>
        <div class="filter-actions"><button class="button button-secondary" type="button" @click="clearFilters">清除筛选</button></div>
      </section>

      <MatchTable :rows="filteredMatches" />
    </main>
  </div>
</template>

<style scoped>
@media (min-width: 901px) { .wide-field { grid-column: span 2; } }
</style>
