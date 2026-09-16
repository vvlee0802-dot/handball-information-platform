<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import {
  createTeam,
  listTeams,
  teamGenderLabels,
  type TeamInput,
  type TeamRecord,
} from '@/services/teams'

const teams = ref<TeamRecord[]>([])
const isLoading = ref(true)
const errorMessage = ref('')
const isSubmitting = ref(false)
const formError = ref('')
const form = reactive<TeamInput>({
  name: '',
  short_name: '',
  city: '',
  country: '',
  gender: 'men',
  description: '',
})

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
    await createTeam({ ...form, description: form.description || null })
    Object.assign(form, {
      name: '',
      short_name: '',
      city: '',
      country: '',
      gender: 'men',
      description: '',
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

      <section class="panel entity-form-panel">
        <h2 class="section-title">新增球队</h2>
        <form @submit.prevent="handleCreate">
          <div class="filter-grid">
            <div class="field">
              <label for="team-name">球队名称</label
              ><input id="team-name" v-model="form.name" required maxlength="120" />
            </div>
            <div class="field">
              <label for="team-short-name">简称</label
              ><input id="team-short-name" v-model="form.short_name" required maxlength="50" />
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
            <div class="field field-wide">
              <label for="team-description">简介</label
              ><input id="team-description" v-model="form.description" maxlength="500" />
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
      <section v-else class="entity-grid">
        <RouterLink
          v-for="team in teams"
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
.field-wide {
  grid-column: span 3;
}
.form-message {
  margin: 16px 0 0;
  font-weight: 650;
}
.form-message-error {
  color: var(--danger);
}
@media (max-width: 900px) {
  .field-wide {
    grid-column: span 1;
  }
}
</style>
