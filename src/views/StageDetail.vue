<template>
  <div class="stage-detail-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title-main">{{ stageInfo.name }}</h2>
    </div>

    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="header-left">
        <h1 class="page-title">比赛详情</h1>
        <div class="filter-tabs">
          <button 
            v-for="tab in genderTabs" 
            :key="tab.value"
            :class="['filter-tab', { active: selectedGender === tab.value }]"
            @click="selectedGender = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
      <nav class="header-nav">
        <RouterLink to="/" class="nav-link">首页</RouterLink>
        <RouterLink to="/teams" class="nav-link">队伍</RouterLink>
        <RouterLink to="/players" class="nav-link">运动员</RouterLink>
      </nav>
    </header>

    <!-- 内容包裹层 -->
    <div class="content-wrapper">
      <main class="main-content">
        <!-- 返回按钮 -->
        <button class="back-btn" @click="$router.back()">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>

        <!-- 阶段介绍卡片 -->
        <div class="stage-info-card">
          <!-- 图标区域 -->
          <div class="icon-container">
            <svg class="stage-icon" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M40 30 L40 170 M40 30 Q140 50, 140 90 Q140 130, 40 150" 
                    stroke="#333" 
                    stroke-width="3" 
                    fill="none" 
                    stroke-linecap="round"/>
              <path d="M40 30 Q140 50, 140 90 Q140 130, 40 150 L40 30" 
                    fill="#f0f0f0" 
                    stroke="#333" 
                    stroke-width="2"/>
            </svg>
          </div>

          <!-- 阶段介绍 -->
          <div class="stage-intro">
            <p class="intro-text">介绍：{{ stageInfo.introduction }}</p>
          </div>
        </div>

        <!-- 搜索筛选栏 -->
        <div class="search-panel">
          <div class="search-row">
            <div class="search-field">
              <label class="field-label">比赛名称：</label>
              <input 
                v-model="searchForm.name" 
                type="text" 
                class="text-input"
              />
            </div>
            
            <div class="search-field">
              <label class="field-label">比赛队伍：</label>
              <input 
                v-model="searchForm.teams" 
                type="text" 
                class="text-input"
              />
            </div>
            
            <div class="search-field">
              <label class="field-label">比赛阶段：</label>
              <input 
                v-model="searchForm.stage" 
                type="text" 
                class="text-input"
              />
            </div>
          </div>

          <div class="search-row">
            <div class="search-field">
              <label class="field-label">高级筛选</label>
              <select v-model="searchForm.advanced" class="select-input">
                <option value="">请选择</option>
                <option value="option1">选项1</option>
              </select>
            </div>

            <div class="search-field">
              <label class="field-label">比赛地点：</label>
              <input 
                v-model="searchForm.location" 
                type="text" 
                class="text-input"
              />
            </div>
            
            <div class="search-field">
              <label class="field-label">比赛状态</label>
              <select v-model="searchForm.status" class="select-input">
                <option value="">请选择</option>
                <option value="已结束">已结束</option>
                <option value="进行中">进行中</option>
                <option value="未开始">未开始</option>
              </select>
            </div>
            
            <div class="search-field">
              <label class="field-label">比赛时间</label>
              <select v-model="searchForm.time" class="select-input">
                <option value="">请选择</option>
                <option value="today">今天</option>
                <option value="week">本周</option>
              </select>
            </div>

            <!-- 按钮组 -->
            <div class="button-group">
              <button class="reset-btn" @click="resetSearch">重置</button>
              <button class="search-btn" @click="handleSearch">搜索</button>
            </div>
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
              <tr 
                v-for="match in filteredMatches" 
                :key="match.id"
                @click="handleMatchClick(match)"
                class="clickable-row"
              >
                <td>{{ match.name }}</td>
                <td>{{ match.date }}</td>
                <td 
                  class="location-clickable"
                  @click.stop="handleVenueClick(match.location)"
                >
                  {{ match.location }}
                </td>
                <td>
                  <div class="teams-cell">
                    <span>{{ match.teamA }}</span>
                    <span class="vs">vs</span>
                    <span :class="{ 'highlight': match.winner === 'B' }">{{ match.teamB }}</span>
                  </div>
                </td>
                <td>{{ match.stage }}</td>
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
import { venues } from '@/data/handball'

interface LegacyMatch {
  id: number
  name: string
  date: string
  location: string
  teamA: string
  teamB: string
  winner: 'A' | 'B'
  stage: string
  status: string
  group: string
}

const route = useRoute()
const router = useRouter()

// 性别筛选
const genderTabs = [
  { label: '全部', value: 'all' },
  { label: '男子', value: 'male' },
  { label: '女子', value: 'female' }
]
const selectedGender = ref('all')

// 阶段信息
const stageInfo = ref({
  name: '淘汰赛',
  introduction: '淘汰赛是一种比赛制度...'
})

// 搜索表单
const searchForm = ref({
  name: '',
  teams: '',
  stage: '',
  advanced: '',
  location: '',
  status: '',
  time: ''
})

// 该阶段的比赛列表
const matches = ref<LegacyMatch[]>([
  {
    id: 1,
    name: '东京奥运会',
    date: '2021/8/2',
    location: '国立代代木竞技场',
    teamA: '挪威24',
    teamB: '25丹麦',
    winner: 'B',
    stage: '淘汰赛',
    status: '已结束',
    group: '男子组'
  },
  {
    id: 2,
    name: '东京奥运会',
    date: '2021/8/4',
    location: '国立代代木竞技场',
    teamA: '法国20',
    teamB: '26丹麦',
    winner: 'B',
    stage: '淘汰赛',
    status: '已结束',
    group: '男子组'
  },
  {
    id: 3,
    name: '世界杯',
    date: '2023/6/15',
    location: '柏林体育馆',
    teamA: '德国25',
    teamB: '西班牙24',
    winner: 'A',
    stage: '淘汰赛',
    status: '已结束',
    group: '女子组'
  }
])

// 筛选后的比赛列表
const filteredMatches = computed(() => {
  let result = matches.value

  // 根据性别筛选
  if (selectedGender.value !== 'all') {
    const groupFilter = selectedGender.value === 'male' ? '男子组' : '女子组'
    result = result.filter(m => m.group === groupFilter)
  }

  // 根据搜索条件筛选
  if (searchForm.value.name) {
    result = result.filter(m => m.name.includes(searchForm.value.name))
  }

  if (searchForm.value.teams) {
    result = result.filter(m => 
      m.teamA.includes(searchForm.value.teams) || 
      m.teamB.includes(searchForm.value.teams)
    )
  }

  if (searchForm.value.stage) {
    result = result.filter(m => m.stage.includes(searchForm.value.stage))
  }

  if (searchForm.value.location) {
    result = result.filter(m => m.location.includes(searchForm.value.location))
  }

  if (searchForm.value.status) {
    result = result.filter(m => m.status === searchForm.value.status)
  }

  return result
})

// 重置搜索
const resetSearch = () => {
  searchForm.value = {
    name: '',
    teams: '',
    stage: '',
    advanced: '',
    location: '',
    status: '',
    time: ''
  }
}

// 执行搜索
const handleSearch = () => {
  console.log('执行搜索', searchForm.value)
}

// 点击比赛行
const handleMatchClick = (match: LegacyMatch) => {
  router.push({
    name: 'match-detail',
    params: { matchId: match.id }
  })
}

// 跳转到场馆详情
const handleVenueClick = (venueName: string) => {
  const venue = venues.find((item) => item.name === venueName)
  if (venue) {
    router.push({
      name: 'venue-detail',
      params: { venueId: venue.id }
    })
  }
}

// 加载阶段数据
onMounted(() => {
  const stageName = route.params.stageName || route.query.stage
  if (stageName) {
    stageInfo.value.name = String(stageName)
    // 这里可以根据 stageName 调用 API 获取阶段详情和比赛列表
    // loadStageData(stageName)
  }
})
</script>

<style scoped>
/* ===== 页面容器 ===== */
.stage-detail-page {
  width: 100vw;
  min-height: 100vh;
  background: #f5f5f5;
  overflow-x: hidden;
}

/* ===== 页面标题 ===== */
.page-header {
  background: #e8e8e8;
  padding: 16px 32px;
  border-bottom: 1px solid #ccc;
}

.page-title-main {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #333;
}

/* ===== 顶部导航栏 ===== */
.header {
  width: 100%;
  background: #e0e0e0;
  padding: 16px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ccc;
  box-sizing: border-box;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #222;
}

.filter-tabs {
  display: flex;
  gap: 4px;
}

.filter-tab {
  padding: 6px 12px;
  border: none;
  background: transparent;
  font-size: 15px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.filter-tab.active {
  color: #222;
  font-weight: 600;
}

.filter-tab:hover {
  color: #222;
}

.header-nav {
  display: flex;
  gap: 32px;
}

.nav-link {
  text-decoration: none;
  color: #222;
  font-size: 16px;
  font-weight: 500;
  transition: color 0.2s;
}

.nav-link:hover {
  color: #000;
}

/* ===== 内容包裹层 ===== */
.content-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
  padding-bottom: 60px;
}

/* ===== 主内容区 ===== */
.main-content {
  width: 100%;
  max-width: 1400px;
  padding: 60px 32px 0;
  position: relative;
  box-sizing: border-box;
}

/* ===== 返回按钮 ===== */
.back-btn {
  position: absolute;
  top: 20px;
  left: 32px;
  width: 40px;
  height: 40px;
  border: 2px solid #222;
  border-radius: 50%;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 10;
}

.back-btn:hover {
  background: #f5f5f5;
  transform: scale(1.05);
}

/* ===== 阶段介绍卡片 ===== */
.stage-info-card {
  background: #d0d0d0;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 24px;
  box-sizing: border-box;
}

.icon-container {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
}

.stage-icon {
  width: 80px;
  height: 80px;
}

.stage-intro {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
}

.intro-text {
  margin: 0;
  font-size: 16px;
  color: #333;
  line-height: 1.6;
}

/* ===== 搜索筛选栏 ===== */
.search-panel {
  background: #d0d0d0;
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: #222;
  white-space: nowrap;
}

.text-input {
  width: 140px;
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  box-sizing: border-box;
}

.text-input:focus {
  outline: none;
  border-color: #2196F3;
}

.select-input {
  width: 110px;
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  cursor: pointer;
  box-sizing: border-box;
}

.select-input:focus {
  outline: none;
  border-color: #2196F3;
}

.button-group {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.reset-btn,
.search-btn {
  padding: 6px 20px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.reset-btn {
  background: white;
  color: #666;
  border: 1px solid #ccc;
}

.reset-btn:hover {
  background: #f5f5f5;
  color: #222;
}

.search-btn {
  background: #2196F3;
  color: white;
}

.search-btn:hover {
  background: #1976D2;
}

/* ===== 比赛列表表格 ===== */
.matches-table-container {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.matches-table {
  width: 100%;
  border-collapse: collapse;
}

.matches-table thead {
  background: #a8e6a0;
}

.matches-table th {
  padding: 16px 14px;
  text-align: left;
  font-size: 14px;
  font-weight: 600;
  color: #222;
  border-bottom: 2px solid #90d388;
}

.matches-table tbody tr {
  background: #d4f5d0;
  border-bottom: 1px solid #b8e8b3;
  transition: background 0.2s;
}

.matches-table tbody tr.clickable-row {
  cursor: pointer;
}

.matches-table tbody tr.clickable-row:hover {
  background: #c5f0c0;
}

.matches-table tbody tr:last-child {
  border-bottom: none;
}

.matches-table td {
  padding: 14px;
  font-size: 13px;
  color: #333;
}

/* 可点击的场馆地点 */
.location-clickable {
  cursor: pointer;
  color: #2196F3;
  transition: all 0.2s;
  font-weight: 500;
}

.location-clickable:hover {
  color: #1976D2;
  text-decoration: underline;
}

/* 队伍单元格 */
.teams-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.teams-cell .vs {
  color: #999;
  font-size: 12px;
}

.teams-cell .highlight {
  color: #d32f2f;
  font-weight: 600;
}

/* ===== 响应式设计 ===== */
@media (max-width: 1024px) {
  .stage-info-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: 12px 20px;
  }

  .header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
    padding: 12px 20px;
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .main-content {
    padding: 60px 20px 0;
  }

  .stage-info-card {
    padding: 20px;
  }

  .stage-intro {
    padding: 20px;
  }

  .search-panel {
    padding: 16px 20px;
  }

  .search-row {
    flex-direction: column;
    align-items: stretch;
  }

  .search-field {
    width: 100%;
  }

  .text-input,
  .select-input {
    width: 100%;
  }

  .button-group {
    margin-left: 0;
    width: 100%;
  }

  .reset-btn,
  .search-btn {
    flex: 1;
  }

  .matches-table-container {
    overflow-x: auto;
  }

  .matches-table {
    min-width: 900px;
  }

  .back-btn {
    left: 20px;
    top: 15px;
  }
}
</style>
