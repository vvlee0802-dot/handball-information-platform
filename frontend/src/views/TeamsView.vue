<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import {
  createTeam,
  listTeams,
  teamGenderLabels,
  type TeamInput,
  type TeamRecord,
} from '@/services/teams'

const authStore = useAuthStore()
const teams = ref<TeamRecord[]>([])
const isLoading = ref(true)
const errorMessage = ref('')
const isSubmitting = ref(false)
const formError = ref('')
const filters = reactive({ name: '', country: '', city: '', gender: '' })
const form = reactive<Omit<TeamInput, 'short_name' | 'description'>>({
  name: '',
  city: '',
  country: '',
  gender: 'men',
})
const visibleTeams = computed(() => {
  const name = filters.name.trim().toLocaleLowerCase('zh-CN')
  const country = filters.country.trim().toLocaleLowerCase('zh-CN')
  const city = filters.city.trim().toLocaleLowerCase('zh-CN')
  return teams.value.filter(
    (team) =>
      (!name || team.name.toLocaleLowerCase('zh-CN').includes(name)) &&
      (!country || team.country.toLocaleLowerCase('zh-CN').includes(country)) &&
      (!city || team.city.toLocaleLowerCase('zh-CN').includes(city)) &&
      (!filters.gender || team.gender === filters.gender),
  )
})

const clearFilters = () => Object.assign(filters, { name: '', country: '', city: '', gender: '' })

const loadTeams = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    teams.value = await listTeams()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '球队加载失败'
  } finally {
    isLoading.value = false
  }
}

const handleCreate = async () => {
  formError.value = ''
  isSubmitting.value = true
  try {
    await createTeam({
      ...form,
      short_name: form.name.trim().slice(0, 50),
      description: null,
    })
    Object.assign(form, {
      name: '',
      city: '',
      country: '',
      gender: 'men',
    })
    await loadTeams()
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '球队创建失败'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadTeams)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Teams</p>
          <h1>球队</h1>
          <p class="page-description">查看并维护球队基础资料。</p>
        </div>
      </header>

      <section class="panel search-panel" aria-labelledby="team-search-title">
        <div class="search-heading">
          <div>
            <h2 id="team-search-title" class="section-title">搜索球队</h2>
            <p>按球队名称、国家或地区、城市和组别筛选。</p>
          </div>
          <span class="meta-chip">{{ visibleTeams.length }} 支球队</span>
        </div>
        <div class="filter-grid">
          <div class="field">
            <label for="team-name-filter">球队名称</label>
            <input id="team-name-filter" v-model="filters.name" type="search" placeholder="输入球队名称" />
          </div>
          <div class="field">
            <label for="team-country-filter">国家或地区</label>
            <input id="team-country-filter" v-model="filters.country" type="search" placeholder="输入国家或地区" />
          </div>
          <div class="field">
            <label for="team-city-filter">所在城市</label>
            <input id="team-city-filter" v-model="filters.city" type="search" placeholder="输入城市" />
          </div>
          <div class="field">
            <label for="team-gender-filter">组别</label>
            <select id="team-gender-filter" v-model="filters.gender">
              <option value="">全部组别</option>
              <option value="men">男子</option>
              <option value="women">女子</option>
            </select>
          </div>
        </div>
        <div class="filter-actions">
          <button class="button button-secondary" type="button" @click="clearFilters">清除筛选</button>
        </div>
      </section>

      <section v-if="authStore.hasPermission('manage_competition_data')" class="panel entity-form-panel">
        <h2 class="section-title">新增球队</h2>
        <form @submit.prevent="handleCreate">
          <div class="filter-grid">
            <div class="field">
              <label for="team-name">球队名称</label
              ><input id="team-name" v-model="form.name" required maxlength="120" />
            </div>
            <div class="field">
              <label for="team-country">国家或地区</label
              ><input id="team-country" v-model="form.country" required maxlength="80" />
            </div>
            <div class="field">
              <label for="team-city">所在城市</label
              ><input id="team-city" v-model="form.city" required maxlength="80" />
            </div>
            <div class="field">
              <label for="team-gender">组别</label
              ><select id="team-gender" v-model="form.gender">
                <option value="men">男子</option>
                <option value="women">女子</option>
              </select>
            </div>
          </div>
          <p v-if="formError" class="form-message form-message-error">创建失败：{{ formError }}</p>
          <div class="filter-actions">
            <button class="button button-primary" type="submit" :disabled="isSubmitting">
              {{ isSubmitting ? '正在保存…' : '创建球队' }}
            </button>
          </div>
        </form>
      </section>

      <div v-if="isLoading" class="panel empty-state">正在从后端加载球队…</div>
      <div v-else-if="errorMessage" class="panel empty-state">
        <p>无法连接球队服务：{{ errorMessage }}</p>
        <button class="button button-secondary" type="button" @click="loadTeams">重新加载</button>
      </div>
      <div v-else-if="teams.length === 0" class="panel empty-state">
        数据库中还没有球队，请使用上方表单创建第一支球队。
      </div>
      <div v-else-if="visibleTeams.length === 0" class="panel empty-state">
        没有符合当前条件的球队。
      </div>
      <section v-else class="entity-grid">
        <RouterLink
          v-for="team in visibleTeams"
          :key="team.id"
          class="list-card"
          :to="{ name: 'team-detail', params: { teamId: team.id } }"
        >
          <span class="meta-chip">{{ teamGenderLabels[team.gender] }} · {{ team.country }}</span>
          <div>
            <h2>{{ team.name }}</h2>
            <p>{{ team.description || `${team.city} · ${team.short_name}` }}</p>
          </div>
          <span class="card-footer">查看球队详情 →</span>
        </RouterLink>
      </section>
    </main>
  </div>
</template>

<style scoped>
.entity-form-panel {
  margin-bottom: 24px;
}
.search-panel { margin-bottom: 20px; }
.search-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.search-heading .section-title { margin-bottom: 3px; }
.search-heading p { margin: 0; color: var(--muted-strong); font-size: 13px; }
.form-message {
  margin: 16px 0 0;
  font-weight: 650;
}
.form-message-error {
  color: var(--danger);
}
@media (max-width: 620px) {
  .search-heading { flex-direction: column; }
}
</style>
