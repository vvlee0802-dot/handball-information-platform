<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { createVenue, listVenues, type VenueInput, type VenueRecord } from '@/services/venues'

const authStore = useAuthStore()
const venues = ref<VenueRecord[]>([])
const isLoading = ref(true)
const errorMessage = ref('')
const isSubmitting = ref(false)
const formError = ref('')
const filters = reactive({ keyword: '', city: '', capacity_min: '', capacity_max: '' })
const form = reactive<Omit<VenueInput, 'description'>>({
  name: '',
  city: '',
  address: '',
  capacity: 0,
})
const visibleVenues = computed(() => {
  const keyword = filters.keyword.trim().toLocaleLowerCase('zh-CN')
  const city = filters.city.trim().toLocaleLowerCase('zh-CN')
  return venues.value.filter((venue) => {
    const searchable = `${venue.name} ${venue.address}`.toLocaleLowerCase('zh-CN')
    return (
      (!keyword || searchable.includes(keyword)) &&
      (!city || venue.city.toLocaleLowerCase('zh-CN').includes(city)) &&
      (!filters.capacity_min || venue.capacity >= Number(filters.capacity_min)) &&
      (!filters.capacity_max || venue.capacity <= Number(filters.capacity_max))
    )
  })
})

const clearFilters = () =>
  Object.assign(filters, { keyword: '', city: '', capacity_min: '', capacity_max: '' })

const loadVenues = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    venues.value = await listVenues()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '场馆加载失败'
  } finally {
    isLoading.value = false
  }
}

const handleCreate = async () => {
  formError.value = ''
  isSubmitting.value = true
  try {
    await createVenue({ ...form, description: null })
    Object.assign(form, { name: '', city: '', address: '', capacity: 0 })
    await loadVenues()
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '场馆创建失败'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadVenues)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Venues</p>
          <h1>场馆</h1>
          <p class="page-description">浏览并维护比赛场馆资料。</p>
        </div>
      </header>

      <section class="panel search-panel" aria-labelledby="venue-search-title">
        <div class="search-heading">
          <div>
            <h2 id="venue-search-title" class="section-title">搜索场馆</h2>
            <p>按名称、地址、城市和容量范围查找场馆。</p>
          </div>
          <span class="meta-chip">{{ visibleVenues.length }} 个场馆</span>
        </div>
        <div class="filter-grid">
          <div class="field">
            <label for="venue-keyword-filter">名称或地址</label>
            <input id="venue-keyword-filter" v-model="filters.keyword" type="search" placeholder="输入名称或地址" />
          </div>
          <div class="field">
            <label for="venue-city-filter">所在城市</label>
            <input id="venue-city-filter" v-model="filters.city" type="search" placeholder="输入城市" />
          </div>
          <div class="field">
            <label for="venue-capacity-min-filter">最小容量</label>
            <input id="venue-capacity-min-filter" v-model="filters.capacity_min" type="number" min="0" placeholder="不限" />
          </div>
          <div class="field">
            <label for="venue-capacity-max-filter">最大容量</label>
            <input id="venue-capacity-max-filter" v-model="filters.capacity_max" type="number" min="0" placeholder="不限" />
          </div>
        </div>
        <div class="filter-actions">
          <button class="button button-secondary" type="button" @click="clearFilters">清除筛选</button>
        </div>
      </section>

      <section v-if="authStore.hasPermission('manage_competition_data')" class="panel entity-form-panel">
        <h2 class="section-title">新增场馆</h2>
        <form @submit.prevent="handleCreate">
          <div class="filter-grid">
            <div class="field">
              <label for="venue-name">场馆名称</label
              ><input id="venue-name" v-model="form.name" required maxlength="120" />
            </div>
            <div class="field">
              <label for="venue-city">所在城市</label
              ><input id="venue-city" v-model="form.city" required maxlength="80" />
            </div>
            <div class="field">
              <label for="venue-address">详细地址</label
              ><input id="venue-address" v-model="form.address" required maxlength="200" />
            </div>
            <div class="field">
              <label for="venue-capacity">容量</label
              ><input
                id="venue-capacity"
                v-model.number="form.capacity"
                type="number"
                required
                min="0"
                max="1000000"
              />
            </div>
          </div>
          <p v-if="formError" class="form-message form-message-error">创建失败：{{ formError }}</p>
          <div class="filter-actions">
            <button class="button button-primary" type="submit" :disabled="isSubmitting">
              {{ isSubmitting ? '正在保存…' : '创建场馆' }}
            </button>
          </div>
        </form>
      </section>

      <div v-if="isLoading" class="panel empty-state">正在从后端加载场馆…</div>
      <div v-else-if="errorMessage" class="panel empty-state">
        <p>无法连接场馆服务：{{ errorMessage }}</p>
        <button class="button button-secondary" type="button" @click="loadVenues">重新加载</button>
      </div>
      <div v-else-if="venues.length === 0" class="panel empty-state">
        数据库中还没有场馆，请使用上方表单创建第一个场馆。
      </div>
      <div v-else-if="visibleVenues.length === 0" class="panel empty-state">
        没有符合当前条件的场馆。
      </div>
      <section v-else class="entity-grid">
        <RouterLink
          v-for="venue in visibleVenues"
          :key="venue.id"
          class="list-card"
          :to="{ name: 'venue-detail', params: { venueId: venue.id } }"
        >
          <span class="meta-chip">{{ venue.city }}</span>
          <div>
            <h2>{{ venue.name }}</h2>
            <p>{{ venue.address }}</p>
          </div>
          <span class="card-footer">容量 {{ venue.capacity.toLocaleString('zh-CN') }} 人 →</span>
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
