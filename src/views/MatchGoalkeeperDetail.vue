<template>
  <div class="player-match-page">
    <header class="header">
      <div class="header-left">
        <h1 class="page-title">队伍详情</h1>
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

      <section class="profile-card">
        <div class="flag-box">
          <svg class="flag-icon" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M48 132V32M48 32C88 18 112 54 152 38V96C112 112 88 76 48 90" stroke="#222" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <div class="intro-box">介绍：{{ playerName }} 守门员简介</div>
      </section>

      <section class="stats-card">
        <table class="detail-table">
          <thead>
            <tr>
              <th></th>
              <th>封挡率</th>
              <th colspan="3">封挡时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stat in stats" :key="stat.type">
              <td class="type-cell">{{ stat.type }}</td>
              <td>{{ stat.rate }}</td>
              <td v-for="save in stat.saves" :key="save.id">
                <span v-if="save.time" class="shot-time">
                  {{ save.time }}
                  <button class="video-btn" @click="playVideo(save.videoUrl)">▻</button>
                </span>
              </td>
              <td v-for="index in Math.max(0, 3 - stat.saves.length)" :key="`empty-${stat.type}-${index}`"></td>
            </tr>
            <tr v-for="index in 4" :key="`blank-${index}`" class="blank-row">
              <td v-for="cell in 5" :key="cell"></td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const matchId = computed(() => String(route.params.matchId))
const playerName = computed(() => String(route.query.player ?? `守门员${route.params.playerId}`))

const stats = [
  { type: '远射', rate: '8/10', saves: [{ id: 1, time: '1:05', videoUrl: '#' }] },
  { type: '近射', rate: '', saves: [] },
  { type: '边射', rate: '', saves: [] },
  { type: '七米球', rate: '', saves: [] },
  { type: '快攻', rate: '', saves: [] },
]

const playVideo = (url: string) => {
  console.log('播放视频:', url)
}
</script>

<style scoped>
.player-match-page {
  width: 100vw;
  min-height: 100vh;
  background: #f4f4f4;
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

.role-tab,
.nav-link {
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

.content {
  max-width: 980px;
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

.profile-card {
  background: #d8d8d8;
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 64px;
  padding: 22px;
  margin-bottom: 48px;
}

.flag-box,
.intro-box {
  min-height: 150px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 2px 3px rgba(0, 0, 0, 0.2);
}

.flag-box {
  display: flex;
  align-items: center;
  justify-content: center;
}

.flag-icon {
  width: 120px;
}

.intro-box {
  padding: 24px;
  box-sizing: border-box;
  text-align: center;
}

.stats-card {
  overflow-x: auto;
}

.detail-table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  table-layout: fixed;
  background: #bdf8ca;
}

.detail-table th,
.detail-table td {
  border: 1px solid rgba(40, 100, 60, 0.45);
  height: 60px;
  text-align: center;
  font-size: 15px;
}

.type-cell {
  font-weight: 700;
}

.blank-row td {
  height: 68px;
}

.shot-time {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.video-btn {
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

@media (max-width: 760px) {
  .header {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .profile-card {
    grid-template-columns: 1fr;
    gap: 18px;
  }
}
</style>
