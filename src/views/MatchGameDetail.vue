<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import NotFoundPanel from '@/components/NotFoundPanel.vue'
import { analysisStatusLabels, getCompetition, getMatch, getTeam, getVenue, videoStatusLabels } from '@/data/handball'

const route = useRoute()
const match = computed(() => getMatch(String(route.params.matchId)))
const teamA = computed(() => match.value ? getTeam(match.value.teamAId) : undefined)
const teamB = computed(() => match.value ? getTeam(match.value.teamBId) : undefined)
const competition = computed(() => match.value ? getCompetition(match.value.competitionId) : undefined)
const venue = computed(() => match.value ? getVenue(match.value.venueId) : undefined)

const videoClass = computed(() => ({
  'status-ready': match.value?.videoStatus === 'ready',
  'status-processing': ['uploaded', 'processing'].includes(match.value?.videoStatus ?? ''),
  'status-failed': match.value?.videoStatus === 'failed',
  'status-neutral': match.value?.videoStatus === 'none',
}))

const analysisClass = computed(() => ({
  'status-ready': match.value?.analysisStatus === 'completed',
  'status-processing': match.value?.analysisStatus === 'processing',
  'status-failed': match.value?.analysisStatus === 'failed',
  'status-neutral': match.value?.analysisStatus === 'not_started',
}))
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <RouterLink class="back-link" to="/matches">← 返回比赛列表</RouterLink>
      <NotFoundPanel v-if="!match" entity="比赛" />

      <template v-else>
        <section class="detail-card score-card">
          <div class="detail-header">
            <div>
              <p class="eyebrow">{{ competition?.name }}</p>
              <h1 class="detail-title">{{ teamA?.shortName }} vs {{ teamB?.shortName }}</h1>
              <div class="detail-meta">
                <span class="meta-chip">{{ match.stage }}</span>
                <span class="meta-chip">{{ match.status }}</span>
                <span class="meta-chip">{{ match.date }} {{ match.startTime }}</span>
              </div>
            </div>
            <div class="score-value">{{ match.scoreA ?? '—' }}<span>:</span>{{ match.scoreB ?? '—' }}</div>
          </div>

          <dl class="info-list">
            <div><dt>赛事</dt><dd><RouterLink :to="{ name: 'competition-detail', params: { competitionId: match.competitionId } }">{{ competition?.name }}</RouterLink></dd></div>
            <div><dt>场馆</dt><dd><RouterLink :to="{ name: 'venue-detail', params: { venueId: match.venueId } }">{{ venue?.name }} · {{ venue?.city }}</RouterLink></dd></div>
            <div><dt>主队</dt><dd><RouterLink :to="{ name: 'team-detail', params: { teamId: match.teamAId } }">{{ teamA?.name }}</RouterLink></dd></div>
            <div><dt>客队</dt><dd><RouterLink :to="{ name: 'team-detail', params: { teamId: match.teamBId } }">{{ teamB?.name }}</RouterLink></dd></div>
          </dl>
        </section>

        <div class="detail-grid">
          <section class="detail-card">
            <p class="eyebrow">Video</p>
            <h2 class="section-title">比赛录像</h2>
            <div class="status-line"><span>录像状态</span><span class="status-badge" :class="videoClass">{{ videoStatusLabels[match.videoStatus] }}</span></div>
            <p class="card-copy">比赛信息与录像分析通过这里衔接。Epic 1 提供入口和状态展示，实际上传处理属于 Epic 2。</p>
            <RouterLink v-if="match.videoStatus === 'none' || match.videoStatus === 'failed'" class="button button-primary" :to="{ name: 'match-upload', params: { matchId: match.id } }">
              {{ match.videoStatus === 'failed' ? '重新上传录像' : '上传录像' }}
            </RouterLink>
            <button v-else-if="match.videoStatus === 'processing' || match.videoStatus === 'uploaded'" class="button button-secondary" disabled>录像处理中</button>
            <RouterLink v-else class="button button-secondary" :to="{ name: 'match-analysis', params: { matchId: match.id } }">打开录像</RouterLink>
          </section>

          <section class="detail-card">
            <p class="eyebrow">AI Analysis</p>
            <h2 class="section-title">分析状态</h2>
            <div class="status-line"><span>当前状态</span><span class="status-badge" :class="analysisClass">{{ analysisStatusLabels[match.analysisStatus] }}</span></div>
            <p class="card-copy">分析完成后，可从比赛详情进入事件审核页面。具体事件识别与审核将在后续 Epic 中实现。</p>
            <RouterLink v-if="match.analysisStatus === 'completed'" class="button button-primary" :to="{ name: 'match-analysis', params: { matchId: match.id } }">查看分析</RouterLink>
            <button v-else class="button button-secondary" disabled>{{ match.analysisStatus === 'processing' ? '分析进行中' : '等待可用录像' }}</button>
          </section>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.score-card a { color: var(--primary-dark); font-weight: 720; }
.score-value { display: flex; align-items: center; gap: 16px; color: var(--ink); font-size: clamp(44px, 7vw, 72px); font-weight: 820; line-height: 1; letter-spacing: -.06em; }
.score-value span { color: var(--muted); font-size: .55em; }
.status-line { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.card-copy { min-height: 72px; margin: 18px 0; color: var(--muted-strong); }
</style>
