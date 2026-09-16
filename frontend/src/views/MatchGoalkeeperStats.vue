<template>
  <div class="match-stats-page">
    <header class="header">
      <div class="header-left">
        <h1 class="page-title">比赛详情</h1>
        <div class="role-tabs">
          <RouterLink class="role-tab" :to="{ name: 'player-stats', params: { matchId } }">非守门员</RouterLink>
          <span class="role-tab active">守门员</span>
        </div>
      </div>
      <nav class="header-nav">
        <RouterLink to="/" class="nav-link">首页</RouterLink>
        <RouterLink to="/teams" class="nav-link">队伍</RouterLink>
        <RouterLink to="/players" class="nav-link">运动员</RouterLink>
      </nav>
    </header>

    <main class="content">
      <button class="back-btn" @click="$router.back()">‹</button>

      <section class="match-table-card">
        <table class="match-table">
          <thead>
            <tr>
              <th colspan="9" class="match-title">东京奥运会手球比赛男子组小组赛A组</th>
            </tr>
            <tr>
              <th colspan="2">法国</th>
              <th colspan="2">20</th>
              <th>26</th>
              <th colspan="4">丹麦</th>
            </tr>
            <tr>
              <th>号码</th>
              <th>姓名</th>
              <th>阻止得分</th>
              <th>封挡</th>
              <th>时间</th>
              <th>封挡</th>
              <th>阻止得分</th>
              <th>号码</th>
              <th>姓名</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.id"
              class="player-row"
              @click="goToDetail(row)"
            >
              <td>{{ row.numberA }}</td>
              <td>{{ row.nameA }}</td>
              <td>{{ row.preventedA }}</td>
              <td>
                <span v-for="save in row.savesA" :key="save.id" class="event-pill">
                  {{ save.label }}
                  <button class="video-btn" @click.stop="playVideo(save.videoUrl)">▻</button>
                </span>
              </td>
              <td class="time-cell">
                <span v-for="time in row.times" :key="time">{{ time }}</span>
              </td>
              <td>
                <span v-for="save in row.savesB" :key="save.id" class="event-pill event-pill--right">
                  {{ save.label }}
                  <button class="video-btn" @click.stop="playVideo(save.videoUrl)">▻</button>
                </span>
              </td>
              <td>{{ row.preventedB }}</td>
              <td>{{ row.numberB }}</td>
              <td>{{ row.nameB }}</td>
            </tr>
            <tr v-for="index in 5" :key="`empty-${index}`" class="empty-row">
              <td v-for="cell in 9" :key="cell"></td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface EventVideo {
  id: number
  label: string
  videoUrl: string
}

interface GoalkeeperStatsRow {
  id: number
  numberA: number
  nameA: string
  preventedA: number
  savesA: EventVideo[]
  times: string[]
  savesB: EventVideo[]
  preventedB: number | string
  numberB: number | string
  nameB: string
}

const route = useRoute()
const router = useRouter()
const matchId = computed(() => String(route.params.matchId))

const rows: GoalkeeperStatsRow[] = [
  {
    id: 1,
    numberA: 1,
    nameA: 'A',
    preventedA: 2,
    savesA: [{ id: 1, label: '1', videoUrl: '#' }],
    times: ['1:02', '2:52'],
    savesB: [{ id: 2, label: '1', videoUrl: '#' }],
    preventedB: 2,
    numberB: 1,
    nameB: 'A',
  },
  {
    id: 2,
    numberA: 2,
    nameA: 'B',
    preventedA: 1,
    savesA: [{ id: 3, label: '1', videoUrl: '#' }, { id: 4, label: '2', videoUrl: '#' }],
    times: ['3:52', '4:52'],
    savesB: [{ id: 5, label: '1', videoUrl: '#' }],
    preventedB: '',
    numberB: '',
    nameB: '',
  },
]

const goToDetail = (row: GoalkeeperStatsRow) => {
  router.push({
    name: 'match-goalkeeper-detail',
    params: { matchId: matchId.value, playerId: row.id },
    query: { player: row.nameA || row.nameB },
  })
}

const playVideo = (url: string) => {
  console.log('播放视频:', url)
}
</script>

<style scoped>
.match-stats-page {
  width: 100vw;
  min-height: 100vh;
  background: #f4f4f4;
  color: #111;
}

.header {
  background: #d8d8d8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 28px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-title {
  margin: 0;
  font-size: 16px;
}

.role-tabs {
  display: flex;
  gap: 28px;
  font-size: 15px;
  font-weight: 600;
}

.role-tab {
  color: #111;
  text-decoration: none;
}

.role-tab.active {
  border-bottom: 2px solid #111;
}

.header-nav {
  display: flex;
  gap: 34px;
}

.nav-link {
  color: #111;
  font-size: 15px;
  text-decoration: none;
}

.content {
  max-width: 1120px;
  margin: 0 auto;
  padding: 28px 28px 64px;
}

.back-btn {
  width: 26px;
  height: 26px;
  border: 1px solid #222;
  border-radius: 999px;
  background: white;
  cursor: pointer;
  font-size: 24px;
  line-height: 20px;
  margin-bottom: 24px;
}

.match-table-card {
  max-width: 920px;
  margin: 0 auto;
}

.match-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #bdf8ca;
}

.match-table th,
.match-table td {
  border: 1px solid rgba(40, 100, 60, 0.45);
  height: 52px;
  text-align: center;
  font-size: 15px;
}

.match-table th {
  font-weight: 700;
}

.match-title {
  height: 58px;
}

.player-row {
  cursor: pointer;
}

.player-row:hover td {
  background: #aef1bc;
}

.empty-row td {
  height: 60px;
}

.time-cell {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.event-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 46px;
  justify-content: center;
  background: #d8d8d8;
  padding: 3px 7px;
  margin: 3px;
}

.event-pill--right {
  background: #e4d5e4;
}

.video-btn {
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  font-size: 12px;
}

@media (max-width: 760px) {
  .header {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .content {
    padding-inline: 16px;
  }

  .match-table-card {
    overflow-x: auto;
  }

  .match-table {
    min-width: 820px;
  }
}
</style>
