<template>
  <div class="match-detail-page">
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <div class="logo-icon">⊞</div>
          <span class="logo-text">手球数据平台</span>
        </div>
      </div>

      <nav class="header-center">
        <RouterLink to="/" class="nav-link">⌂ 首页</RouterLink>
        <button :class="['nav-link', 'nav-btn', { active: activeTab === 'matches' }]" @click="activeTab = 'matches'">
          🤾 比赛
        </button>
        <RouterLink to="/players" class="nav-link">👤 运动员</RouterLink>
      </nav>

      <div class="header-right">
        <div class="gender-tabs">
          <button
            v-for="tab in genderTabs" :key="tab.value"
            :class="['gender-btn', { active: selectedGender === tab.value }]"
            @click="selectedGender = tab.value"
          >{{ tab.label }}</button>
        </div>
        <button class="icon-btn">🔍</button>
      </div>
    </header>

    <div class="content-wrapper">
      <main class="main-content">
        <button class="back-btn" @click="$router.back()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>

        <!-- 比赛介绍卡片 -->
        <div class="match-info-card">
          <div class="flag-container">
            <img
              src="/images/paris2024.png"
              alt="巴黎2024奥运会"
              class="match-logo-img"
            />
          </div>
          <div class="match-intro">
            <h2 class="intro-title">{{ matchInfo.name }}</h2>
            <div class="intro-sections">
              <div v-for="section in matchInfo.sections" :key="section.title" class="intro-section">
                <h3 class="section-title">{{ section.title }}</h3>
                <p class="section-text">{{ section.content }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 分组信息 -->
        <div class="groups-section">
          <div class="group-card">
            <h3 class="group-title">A组</h3>
            <div class="group-content">
              <div v-for="team in groupA" :key="team.id" class="team-item">
                {{ team.name }}
              </div>
            </div>
          </div>
          <div class="group-card">
            <h3 class="group-title">B组</h3>
            <div class="group-content">
              <div v-for="team in groupB" :key="team.id" class="team-item">
                {{ team.name }}
              </div>
            </div>
          </div>
        </div>

        <!-- 排名区域 -->
        <div class="ranking-section">
          <div class="ranking-card">
            <div class="ranking-row header-row">
              <div class="column-title">排名</div>
              <div class="column-title">队伍</div>
            </div>
            <div v-for="rank in rankings" :key="rank.id" class="ranking-row">
              <div class="ranking-item">{{ rank.position }}</div>
              <div class="team-item-clickable" @click="goToTeamDetail(rank)">
                {{ rank.teamName }}
              </div>
            </div>
          </div>
        </div>

        <!-- 搜索面板 -->
        <div class="search-panel">
          <div class="search-row">
            <div class="search-field">
              <label class="field-label">比赛名称</label>
              <input v-model="searchForm.name" type="text" class="text-input" placeholder="请输入比赛名称" />
            </div>
            <div class="search-field">
              <label class="field-label">比赛地点</label>
              <input v-model="searchForm.location" type="text" class="text-input" placeholder="请输入比赛地点" />
            </div>
            <div class="search-field">
              <label class="field-label">比赛时间</label>
              <input v-model="searchForm.timeInput" type="text" class="text-input" placeholder="请选择日期" />
            </div>
          </div>

          <div class="search-row">
            <div class="search-field">
              <label class="field-label">赛道编号</label>
              <div class="select-wrap">
                <select v-model="searchForm.advanced" class="select-input">
                  <option value="">请选择</option>
                  <option value="option1">选项1</option>
                  <option value="option2">选项2</option>
                </select>
                <span class="select-arrow">▾</span>
              </div>
            </div>
            <div class="search-field">
              <label class="field-label">比赛编码</label>
              <input v-model="searchForm.teams" type="text" class="text-input" placeholder="请输入比赛编码" />
            </div>
            <div class="search-field">
              <label class="field-label">比赛状态</label>
              <div class="select-wrap">
                <select v-model="searchForm.status" class="select-input">
                  <option value="">请选择</option>
                  <option value="已结束">已结束</option>
                  <option value="进行中">进行中</option>
                  <option value="未开始">未开始</option>
                </select>
                <span class="select-arrow">▾</span>
              </div>
            </div>
            <div class="search-field">
              <label class="field-label">比赛时段</label>
              <div class="select-wrap">
                <select v-model="searchForm.stage" class="select-input">
                  <option value="">请选择</option>
                  <option value="淘汰赛">淘汰赛</option>
                  <option value="小组赛">小组赛</option>
                  <option value="决赛">决赛</option>
                </select>
                <span class="select-arrow">▾</span>
              </div>
            </div>
          </div>

          <div class="button-row">
            <button class="reset-btn" @click="resetSearch">↺ 重置</button>
            <button class="search-btn" @click="handleSearch">🔍 搜索</button>
          </div>
        </div>

        <!-- 比赛列表表格 -->
        <div class="matches-table-container">
          <table class="matches-table">
            <thead>
              <tr>
                <th>比赛名称</th>
                <th>比赛时间</th>
                <th>比赛地点</th>
                <th>比赛队伍</th>
                <th>比赛阶段</th>
                <th>比赛状态</th>
                <th>比赛组别</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="match in filteredMatches" :key="match.id" class="clickable-row">
                <td>{{ match.name }}</td>
                <td>{{ match.date }}</td>
                <td class="location-clickable" @click.stop="handleVenueClick(match.location)">{{ match.location }}</td>
                <td>
                  <div class="teams-cell">
                    <span>{{ match.teamA }}</span>
                    <span class="vs">vs</span>
                    <span :class="{ highlight: match.winner === 'B' }">{{ match.teamB }}</span>
                  </div>
                </td>
                <td class="stage-clickable" @click.stop="handleStageClick(match.stage)">{{ match.stage }}</td>
                <td>{{ match.status }}</td>
                <td>{{ match.group }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { teams, venues } from '@/data/handball'

interface Ranking {
  id: number
  position: number
  teamName: string
}

const route = useRoute()
const router = useRouter()

const activeTab = ref('matches')

const genderTabs = [
  { label: '全部', value: 'all' },
  { label: '男子', value: 'male' },
  { label: '女子', value: 'female' }
]
const selectedGender = ref('all')

const matchInfo = ref({
  name: '巴黎奥运会',
  sections: [
    {
      title: '标志性场馆',
      content: '2024年巴黎奥运会将光之城的许多标志性地标转变为体育竞技场，呈现出世界从未见过的场景。从埃菲尔铁塔旁的沙滩排球场地，到凡尔赛宫的马术比赛场地，再到大皇宫的击剑赛场，巴黎的许多著名地标成为奥运体育比赛的中心，数百万观众在现场见证了这个法国首都的新面貌，留下了难以忘怀的回忆。'
    },
    {
      title: '性别平等的历史性突破',
      content: '遵循其口号"Games Wide Open"（奥运更开放），2024年巴黎奥运会成为历史上首届在赛场上实现性别平等的奥运会。在提供的10500个运动员席位中，国际奥委会平等分配给了男女运动员。同时，开幕式上96%的国家和地区奥委会选择了一男一女两位运动员共同担任代表团旗手。此外，32个大项中有28个实现了完全性别平等，并且巴黎2024年超一半的奖牌项目对女性运动员开放。'
    }
  ]
})

const groupA = ref([
  { id: 1, name: '法国' },
  { id: 2, name: '德国' },
  { id: 3, name: '西班牙' }
])

const groupB = ref([
  { id: 4, name: '丹麦' },
  { id: 5, name: '挪威' },
  { id: 6, name: '瑞典' }
])

const rankings = ref<Ranking[]>([
  { id: 1, position: 1, teamName: '丹麦' },
  { id: 2, position: 2, teamName: '法国' },
  { id: 3, position: 3, teamName: '挪威' },
  { id: 4, position: 4, teamName: '德国' },
  { id: 5, position: 5, teamName: '西班牙' },
  { id: 6, position: 6, teamName: '瑞典' }
])

const searchForm = ref({
  name: '', location: '', timeInput: '',
  advanced: '', teams: '', status: '', stage: ''
})

const matches = ref([
  {
    id: 1, name: '巴黎奥运会', date: '2024/8/2',
    location: '皮埃尔·莫鲁瓦球场',
    teamA: '挪威24', teamB: '25丹麦', winner: 'B',
    stage: '淘汰赛', status: '已结束', group: '男子组'
  },
  {
    id: 2, name: '巴黎奥运会', date: '2024/8/4',
    location: '皮埃尔·莫鲁瓦球场',
    teamA: '法国20', teamB: '26丹麦', winner: 'B',
    stage: '淘汰赛', status: '已结束', group: '男子组'
  }
])

const filteredMatches = computed(() => {
  let result = matches.value
  if (searchForm.value.name) result = result.filter(m => m.name.includes(searchForm.value.name))
  if (searchForm.value.teams) result = result.filter(m => m.teamA.includes(searchForm.value.teams) || m.teamB.includes(searchForm.value.teams))
  if (searchForm.value.location) result = result.filter(m => m.location.includes(searchForm.value.location))
  if (searchForm.value.status) result = result.filter(m => m.status === searchForm.value.status)
  return result
})

const resetSearch = () => {
  searchForm.value = { name: '', location: '', timeInput: '', advanced: '', teams: '', status: '', stage: '' }
}
const handleSearch = () => console.log('搜索', searchForm.value)
const goToTeamDetail = (rank: Ranking) => {
  const team = teams.find((item) => item.shortName === rank.teamName)
  if (team) router.push({ name: 'team-detail', params: { teamId: team.id } })
}
const handleVenueClick = (venueName: string) => {
  const venue = venues.find((item) => item.name === venueName)
  if (venue) router.push({ name: 'venue-detail', params: { venueId: venue.id } })
}
const handleStageClick = (stageName: string) => router.push({ name: 'matches', query: { stage: stageName } })

onMounted(() => {
  console.log('加载巴黎奥运会详情', route.params.matchId)
})

</script>

<style scoped>
.match-detail-page {
  width: 100vw;
  min-height: 100vh;
  background: #eef1f8;
  overflow-x: hidden;
}

/* ===== Header ===== */
.header {
  width: 100%;
  background: white;
  padding: 0 32px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  box-sizing: border-box;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left { flex: 1; display: flex; align-items: center; }

.logo { display: flex; align-items: center; gap: 8px; }
.logo-icon {
  width: 32px; height: 32px;
  background: #e8eaf0; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; color: #555;
}
.logo-text { font-size: 15px; font-weight: 600; color: #222; }

.header-center {
  flex: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.nav-link {
  text-decoration: none;
  color: #555;
  font-size: 14px;
  padding: 6px 16px;
  border-radius: 8px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}
.nav-link:hover { color: #222; background: #f5f5f5; }

.nav-btn {
  border: none; cursor: pointer;
  font-family: inherit; background: transparent;
}
.nav-btn.active { background: #3b82f6; color: white; font-weight: 600; }
.nav-btn.active:hover { background: #2563eb; }

.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
}

.gender-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 3px;
}

.gender-btn {
  padding: 4px 14px; border: none; border-radius: 6px;
  font-size: 13px; font-weight: 500; cursor: pointer;
  background: transparent; color: #666;
  font-family: inherit; transition: all 0.2s;
}
.gender-btn.active {
  background: white; color: #222; font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.gender-btn:hover:not(.active) { color: #333; }

.icon-btn {
  width: 36px; height: 36px; border: none; border-radius: 50%;
  background: transparent; font-size: 18px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: #555; transition: background 0.2s;
}
.icon-btn:hover { background: #f3f4f6; }

/* ===== Content ===== */
.content-wrapper {
  display: flex;
  justify-content: center;
  padding: 32px;
  box-sizing: border-box;
}

.main-content {
  width: 100%;
  max-width: 1400px;
  position: relative;
}

/* ===== Back btn ===== */
.back-btn {
  width: 36px; height: 36px;
  border: 1.5px solid #bbb; border-radius: 50%;
  background: white; display: flex; align-items: center; justify-content: center;
  cursor: pointer; margin-bottom: 20px; transition: all 0.2s; color: #555;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.back-btn:hover { background: #f0f0f0; border-color: #999; }

/* ===== 比赛介绍卡片 ===== */
.match-info-card {
  background: white;
  border-radius: 16px;
  padding: 28px;
  margin-bottom: 24px;
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 28px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  box-sizing: border-box;
  align-items: start;
}

.flag-container {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: sticky;
  top: 80px;
}

.match-logo-img {
  width: 100%;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
}

.match-intro {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 24px 28px;
}

.intro-title {
  margin: 0 0 20px;
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  padding-bottom: 12px;
  border-bottom: 2px solid #e5e7eb;
}

.intro-sections {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.intro-section { display: flex; flex-direction: column; gap: 8px; }

.section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #3b82f6;
}

.section-text {
  margin: 0;
  font-size: 14px;
  color: #444;
  line-height: 1.8;
  text-align: justify;
}

/* ===== 分组信息 ===== */
.groups-section {
  background: white;
  border: 3px solid #3b82f6;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.group-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  min-height: 150px;
}

.group-title {
  margin: 0 0 16px;
  font-size: 17px;
  font-weight: 600;
  color: #222;
  text-align: center;
}

.group-content { display: flex; flex-direction: column; gap: 8px; }

.team-item {
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  font-size: 14px;
  color: #333;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* ===== 排名区域 ===== */
.ranking-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.ranking-card {
  background: #f8f9fa;
  border-radius: 12px;
  overflow: hidden;
}

.ranking-row {
  display: grid;
  grid-template-columns: 240px 1fr;
  border-bottom: 1px solid #e5e7eb;
}
.ranking-row:last-child { border-bottom: none; }

.ranking-row.header-row {
  background: #f0f2f5;
  border-bottom: 2px solid #e5e7eb;
}

.column-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  text-align: center;
  padding: 16px 20px;
}

.ranking-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 20px;
  font-size: 18px;
  font-weight: 700;
  color: #3b82f6;
  background: #f8f9fa;
  border-right: 1px solid #e5e7eb;
}

.team-item-clickable {
  padding: 16px 24px;
  background: white;
  font-size: 15px;
  font-weight: 500;
  color: #333;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.team-item-clickable:hover { background: #3b82f6; color: white; }

/* ===== 搜索面板 ===== */
.search-panel {
  background: white;
  border-radius: 16px;
  padding: 28px 32px 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-row { display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-end; }

.search-field { display: flex; flex-direction: column; gap: 8px; flex: 1; min-width: 160px; }
.field-label { font-size: 13px; font-weight: 500; color: #333; }

.text-input {
  width: 100%; padding: 10px 14px;
  border: 1px solid #e5e7eb; border-radius: 8px;
  font-size: 14px; background: white;
  box-sizing: border-box; color: #333; transition: border-color 0.2s;
}
.text-input:focus { outline: none; border-color: #3b82f6; }
.text-input::placeholder { color: #aaa; }

.select-wrap { position: relative; }
.select-input {
  width: 100%; padding: 10px 36px 10px 14px;
  border: 1px solid #e5e7eb; border-radius: 8px;
  font-size: 14px; background: white; cursor: pointer;
  appearance: none; -webkit-appearance: none;
  box-sizing: border-box; color: #333;
}
.select-input:focus { outline: none; border-color: #3b82f6; }
.select-arrow {
  position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%); color: #999;
  pointer-events: none; font-size: 12px;
}

.button-row { display: flex; justify-content: flex-end; gap: 12px; }

.reset-btn, .search-btn {
  padding: 9px 22px; border-radius: 8px;
  font-size: 14px; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; gap: 6px;
  transition: all 0.2s; font-family: inherit;
}
.reset-btn { background: white; color: #555; border: 1px solid #ddd; }
.reset-btn:hover { background: #f5f5f5; color: #222; }
.search-btn { background: #3b82f6; color: white; border: none; }
.search-btn:hover { background: #2563eb; }

/* ===== 表格 ===== */
.matches-table-container {
  background: white; border-radius: 16px;
  overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.matches-table { width: 100%; border-collapse: collapse; }
.matches-table thead tr { background: #22c55e; }
.matches-table th {
  padding: 16px 20px; text-align: left;
  font-size: 14px; font-weight: 600; color: white;
}
.matches-table tbody tr { border-bottom: 1px solid #f3f4f6; transition: background 0.15s; }
.matches-table tbody tr.clickable-row { cursor: pointer; }
.matches-table tbody tr:hover { background: #f9fafb; }
.matches-table tbody tr:last-child { border-bottom: none; }
.matches-table td { padding: 18px 20px; font-size: 14px; color: #333; }

.location-clickable { cursor: pointer; }
.location-clickable:hover { color: #3b82f6; text-decoration: underline; }
.stage-clickable { cursor: pointer; color: #3b82f6; }
.stage-clickable:hover { text-decoration: underline; }

.teams-cell { display: flex; align-items: center; gap: 8px; }
.teams-cell .vs { color: #aaa; font-size: 13px; }
.teams-cell .highlight { color: #ef4444; font-weight: 600; }

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .groups-section { grid-template-columns: 1fr; }
  .ranking-row { grid-template-columns: 150px 1fr; }
}

@media (max-width: 768px) {
  .content-wrapper { padding: 16px; }
  .match-info-card {
    grid-template-columns: 1fr;
  }
  .flag-container {
    position: static;
    max-width: 240px;
    margin: 0 auto;
  }
  .matches-table-container { overflow-x: auto; }
  .matches-table { min-width: 800px; }
}
</style>
