<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { listCompetitions } from '@/services/competitions'
import { listMatches } from '@/services/matches'
import { listPlayers } from '@/services/players'
import { listTeams } from '@/services/teams'
import { listVenues } from '@/services/venues'

const counts = reactive({ competitions: 0, matches: 0, teams: 0, players: 0, venues: 0 })
const entries = [
  {
    to: '/competitions',
    label: '赛事',
    key: 'competitions',
    description: '按赛季和赛事查看比赛',
    accent: 'blue',
  },
  {
    to: '/matches',
    label: '比赛',
    key: 'matches',
    description: '筛选比赛并进入详情',
    accent: 'purple',
  },
  { to: '/teams', label: '球队', key: 'teams', description: '查看阵容和相关比赛', accent: 'green' },
  {
    to: '/players',
    label: '球员',
    key: 'players',
    description: '查看号码、位置和所属球队',
    accent: 'orange',
  },
  {
    to: '/venues',
    label: '场馆',
    key: 'venues',
    description: '查看场馆及举办的比赛',
    accent: 'pink',
  },
]
onMounted(async () => {
  try {
    const [c, m, t, p, v] = await Promise.all([
      listCompetitions(),
      listMatches(),
      listTeams(),
      listPlayers(),
      listVenues(),
    ])
    Object.assign(counts, {
      competitions: c.length,
      matches: m.length,
      teams: t.length,
      players: p.length,
      venues: v.length,
    })
  } catch {
    /* 导航仍可使用 */
  }
})
</script>

<template>
  <div class="page-shell home-page">
    <AppHeader />
    <main class="home-content">
      <section class="hero">
        <p class="eyebrow">Handball Information Platform</p>
        <h1>从比赛信息出发，<br /><span>连接每一次赛后分析</span></h1>
        <p>浏览赛事、比赛、球队、球员和场馆，通过统一的信息关系快速找到目标比赛。</p>
        <RouterLink class="button button-primary" to="/matches">查找比赛</RouterLink>
      </section>

      <section class="entry-grid" aria-label="信息入口">
        <RouterLink
          v-for="entry in entries"
          :key="entry.to"
          :to="entry.to"
          class="entry"
          :class="`entry-${entry.accent}`"
        >
          <div class="entry-count">{{ counts[entry.key as keyof typeof counts] }}</div>
          <div>
            <h2>{{ entry.label }}</h2>
            <p>{{ entry.description }}</p>
          </div>
          <span class="entry-arrow">进入 →</span>
        </RouterLink>
      </section>
    </main>
  </div>
</template>

<style scoped>
.home-page {
  background: radial-gradient(circle at 15% 10%, #eef2ff 0, transparent 34%), var(--surface-soft);
}
.home-content {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: 78px 0 72px;
}
.hero {
  max-width: 830px;
}
.hero h1 {
  margin: 0;
  font-size: clamp(42px, 7vw, 76px);
  font-weight: 820;
  line-height: 1.08;
  letter-spacing: -0.055em;
}
.hero h1 span {
  color: var(--primary);
}
.hero > p:not(.eyebrow) {
  max-width: 680px;
  margin: 24px 0 28px;
  color: var(--muted-strong);
  font-size: 18px;
}
.entry-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-top: 72px;
}
.entry {
  display: grid;
  min-height: 220px;
  padding: 20px;
  border: 1px solid var(--border);
  border-top: 4px solid var(--primary);
  border-radius: 16px;
  background: white;
  box-shadow: 0 12px 28px rgba(36, 48, 84, 0.06);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}
.entry:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 36px rgba(36, 48, 84, 0.11);
}
.entry-count {
  color: var(--muted);
  font-size: 13px;
  font-weight: 750;
}
.entry h2 {
  margin: 0 0 5px;
  font-size: 24px;
  font-weight: 780;
}
.entry p {
  margin: 0;
  color: var(--muted-strong);
  font-size: 13px;
}
.entry-arrow {
  align-self: end;
  color: var(--primary);
  font-size: 13px;
  font-weight: 760;
}
.entry-purple {
  border-top-color: #7a54c7;
}
.entry-green {
  border-top-color: #20876b;
}
.entry-orange {
  border-top-color: #d2722d;
}
.entry-pink {
  border-top-color: #c04d79;
}
@media (max-width: 980px) {
  .entry-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 620px) {
  .home-content {
    width: calc(100% - 28px);
    padding-top: 50px;
  }
  .entry-grid {
    grid-template-columns: 1fr;
    margin-top: 48px;
  }
  .entry {
    min-height: 170px;
  }
}
</style>
