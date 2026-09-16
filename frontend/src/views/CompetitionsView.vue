<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import {
  competitionStatusLabels,
  createCompetition,
  listCompetitions,
  type CompetitionInput,
  type CompetitionRecord,
} from '@/services/competitions'

const form = reactive<CompetitionInput>({
  name: '',
  season: '',
  stage: '',
  status: 'draft',
})

const isSubmitting = ref(false)
const formError = ref('')

const competitions = ref<CompetitionRecord[]>([])
const isLoading = ref(true)
const errorMessage = ref('')

const loadCompetitions = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    competitions.value = await listCompetitions()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '赛事加载失败'
  } finally {
    isLoading.value = false
  }
}

const handleCreate = async () => {
  formError.value = ''
  isSubmitting.value = true

  try {
    await createCompetition({
      ...form,
      stage: form.stage || null,
    })

    form.name = ''
    form.season = ''
    form.stage = ''
    form.status = 'draft'

    await loadCompetitions()
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '赛事创建失败'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadCompetitions)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Competitions</p>
          <h1>赛事</h1>
          <p class="page-description">从赛事和赛季进入对应比赛列表。</p>
        </div>
      </header>

      <section class="panel competition-form-panel">
        <h2 class="section-title">新增赛事</h2>

        <form @submit.prevent="handleCreate">
          <div class="filter-grid">
            <div class="field">
              <label for="competition-name">赛事名称</label>
              <input
                id="competition-name"
                v-model="form.name"
                type="text"
                required
                maxlength="120"
                placeholder="例如：全国手球锦标赛"
              />
            </div>

            <div class="field">
              <label for="competition-season">赛季</label>
              <input
                id="competition-season"
                v-model="form.season"
                type="text"
                required
                maxlength="50"
                placeholder="例如：2026"
              />
            </div>

            <div class="field">
              <label for="competition-stage">赛事阶段</label>
              <input
                id="competition-stage"
                v-model="form.stage"
                type="text"
                maxlength="80"
                placeholder="例如：小组赛"
              />
            </div>

            <div class="field">
              <label for="competition-status">状态</label>
              <select id="competition-status" v-model="form.status">
                <option value="draft">草稿</option>
                <option value="active">进行中</option>
                <option value="completed">已结束</option>
                <option value="archived">已归档</option>
              </select>
            </div>
          </div>

          <p v-if="formError" class="page-description">创建失败：{{ formError }}</p>

          <div class="filter-actions">
            <button class="button button-primary" type="submit" :disabled="isSubmitting">
              {{ isSubmitting ? '正在保存…' : '创建赛事' }}
            </button>
          </div>
        </form>
      </section>

      <div v-if="isLoading" class="panel empty-state">正在从后端加载赛事…</div>
      <div v-else-if="errorMessage" class="panel empty-state">
        <p>无法连接赛事服务：{{ errorMessage }}</p>
        <button class="button button-secondary" type="button" @click="loadCompetitions">
          重新加载
        </button>
      </div>
      <div v-else-if="competitions.length === 0" class="panel empty-state">
        数据库中还没有赛事，请使用上方表单创建第一条赛事数据。
      </div>
      <section v-else class="entity-grid">
        <RouterLink
          v-for="item in competitions"
          :key="item.id"
          class="list-card"
          :to="{ name: 'competition-detail', params: { competitionId: item.id } }"
        >
          <span class="meta-chip"
            >{{ item.season }} · {{ competitionStatusLabels[item.status] }}</span
          >
          <div>
            <h2>{{ item.name }}</h2>
            <p>{{ item.stage || '暂未设置赛事阶段' }}</p>
          </div>
          <span class="card-footer">查看赛事详情 →</span>
        </RouterLink>
      </section>
    </main>
  </div>
</template>

<style scoped>
.competition-form-panel {
  margin-bottom: 24px;
}
</style>
