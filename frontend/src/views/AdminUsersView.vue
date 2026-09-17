<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import {
  createAdminUser,
  listAdminUsers,
  updateAdminUser,
  type AdminUser,
  type AdminUserCreate,
} from '@/services/adminUsers'
import type { Permission, UserRole } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const users = ref<AdminUser[]>([])
const isLoading = ref(true)
const isSubmitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const roleOptions: Array<{ value: UserRole; label: string }> = [
  { value: 'athlete', label: '运动员' },
  { value: 'coach_analyst', label: '教练 / 分析师' },
  { value: 'competition_admin', label: '赛事管理员' },
  { value: 'system_admin', label: '系统管理员' },
]

const permissionOptions: Array<{ value: Permission; label: string }> = [
  { value: 'view_authorized_video', label: '查看获授权视频' },
  { value: 'upload_and_annotate_video', label: '上传与标注视频' },
  { value: 'manage_competition_data', label: '维护赛事数据' },
  { value: 'generate_reports', label: '生成报告与提问' },
  { value: 'manage_users', label: '管理用户与系统' },
]

const form = reactive<AdminUserCreate>({
  email: '',
  display_name: '',
  password: '',
  role: 'athlete',
  extra_permissions: [],
})

const canManageUsers = computed(() => authStore.hasPermission('manage_users'))
const roleLabel = (role: UserRole) =>
  roleOptions.find((item) => item.value === role)?.label ?? role
const permissionLabel = (permission: Permission) =>
  permissionOptions.find((item) => item.value === permission)?.label ?? permission

const loadUsers = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    users.value = await listAdminUsers()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '用户加载失败'
  } finally {
    isLoading.value = false
  }
}

const resetForm = () => {
  form.email = ''
  form.display_name = ''
  form.password = ''
  form.role = 'athlete'
  form.extra_permissions = []
}

const handleCreate = async () => {
  isSubmitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await createAdminUser({ ...form })
    resetForm()
    successMessage.value = '用户已创建，可以使用设置的邮箱和密码登录。'
    await loadUsers()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '用户创建失败'
  } finally {
    isSubmitting.value = false
  }
}

const handleRoleChange = async (user: AdminUser, event: Event) => {
  const role = (event.target as HTMLSelectElement).value as UserRole
  errorMessage.value = ''
  try {
    const updated = await updateAdminUser(user.id, { role })
    users.value = users.value.map((item) => (item.id === user.id ? updated : item))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '角色更新失败'
    await loadUsers()
  }
}

const handleActiveChange = async (user: AdminUser, event: Event) => {
  const is_active = (event.target as HTMLInputElement).checked
  errorMessage.value = ''
  try {
    const updated = await updateAdminUser(user.id, { is_active })
    users.value = users.value.map((item) => (item.id === user.id ? updated : item))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '账号状态更新失败'
    await loadUsers()
  }
}

const handleExtraPermissionChange = async (
  user: AdminUser,
  permission: Permission,
  event: Event,
) => {
  const checked = (event.target as HTMLInputElement).checked
  const extra_permissions = checked
    ? [...new Set([...user.extra_permissions, permission])]
    : user.extra_permissions.filter((item) => item !== permission)
  errorMessage.value = ''
  try {
    const updated = await updateAdminUser(user.id, { extra_permissions })
    users.value = users.value.map((item) => (item.id === user.id ? updated : item))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '额外权限更新失败'
    await loadUsers()
  }
}

watch(
  [() => authStore.initialized, canManageUsers],
  ([initialized, allowed]) => {
    if (!initialized) return
    if (allowed) void loadUsers()
    else isLoading.value = false
  },
  { immediate: true },
)
</script>

<template>
  <div class="page-shell">
    <AppHeader />
    <main class="page-container">
      <header class="page-heading">
        <div>
          <p class="eyebrow">Administration</p>
          <h1>用户与角色管理</h1>
          <p class="page-description">由系统管理员创建账号、分配角色及可配置的额外权限。</p>
        </div>
      </header>

      <section v-if="!canManageUsers" class="panel empty-state">
        当前账号没有用户管理权限。即使直接访问本页面，后端也不会返回用户数据。
      </section>

      <template v-else>
        <section class="panel create-panel">
          <h2 class="section-title">创建用户</h2>
          <form @submit.prevent="handleCreate">
            <div class="filter-grid">
              <div class="field">
                <label for="new-display-name">姓名</label>
                <input id="new-display-name" v-model="form.display_name" required maxlength="100" />
              </div>
              <div class="field">
                <label for="new-email">邮箱</label>
                <input id="new-email" v-model="form.email" type="email" required maxlength="254" />
              </div>
              <div class="field">
                <label for="new-password">初始密码</label>
                <input id="new-password" v-model="form.password" type="password" required minlength="8" />
              </div>
              <div class="field">
                <label for="new-role">角色</label>
                <select id="new-role" v-model="form.role">
                  <option v-for="option in roleOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </div>
            </div>

            <fieldset class="permission-fieldset">
              <legend>额外权限（角色默认权限之外）</legend>
              <label v-for="option in permissionOptions" :key="option.value">
                <input v-model="form.extra_permissions" type="checkbox" :value="option.value" />
                {{ option.label }}
              </label>
            </fieldset>

            <p v-if="successMessage" class="message success">{{ successMessage }}</p>
            <p v-if="errorMessage" class="message error">{{ errorMessage }}</p>
            <div class="filter-actions">
              <button class="button button-primary" type="submit" :disabled="isSubmitting">
                {{ isSubmitting ? '正在创建…' : '创建用户' }}
              </button>
            </div>
          </form>
        </section>

        <div v-if="isLoading" class="panel empty-state">正在加载用户…</div>
        <section v-else class="user-grid" aria-label="用户列表">
          <article v-for="user in users" :key="user.id" class="panel user-card">
            <div class="user-heading">
              <div>
                <h2>{{ user.display_name }}</h2>
                <p>{{ user.email }}</p>
              </div>
              <span class="status-badge" :class="user.is_active ? 'status-ready' : 'status-neutral'">
                {{ user.is_active ? '启用' : '停用' }}
              </span>
            </div>

            <div class="field">
              <label :for="`role-${user.id}`">系统角色</label>
              <select
                :id="`role-${user.id}`"
                :value="user.role"
                :disabled="user.id === authStore.user?.id"
                @change="handleRoleChange(user, $event)"
              >
                <option v-for="option in roleOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="permission-list">
              <strong>当前有效权限</strong>
              <span v-for="permission in user.permissions" :key="permission" class="meta-chip">
                {{ permissionLabel(permission) }}
              </span>
              <span v-if="user.permissions.length === 0" class="muted">无</span>
            </div>

            <fieldset class="permission-fieldset user-permissions">
              <legend>额外权限</legend>
              <label v-for="option in permissionOptions" :key="option.value">
                <input
                  type="checkbox"
                  :checked="user.extra_permissions.includes(option.value)"
                  @change="handleExtraPermissionChange(user, option.value, $event)"
                />
                {{ option.label }}
              </label>
            </fieldset>

            <label class="active-toggle">
              <input
                type="checkbox"
                :checked="user.is_active"
                :disabled="user.id === authStore.user?.id"
                @change="handleActiveChange(user, $event)"
              />
              允许该用户登录
            </label>
            <small>{{ roleLabel(user.role) }}{{ user.id === authStore.user?.id ? '（当前账号）' : '' }}</small>
          </article>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.create-panel { margin-bottom: 24px; }
.permission-fieldset { display: flex; flex-wrap: wrap; gap: 12px 20px; margin: 20px 0 0; padding: 16px; border: 1px solid var(--border); border-radius: 12px; }
.permission-fieldset legend { padding: 0 8px; color: var(--muted-strong); font-size: 12px; font-weight: 700; }
.permission-fieldset label,
.active-toggle { display: flex; align-items: center; gap: 7px; color: var(--muted-strong); font-size: 13px; }
.user-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.user-card { display: grid; gap: 18px; }
.user-heading { display: flex; justify-content: space-between; gap: 16px; }
.user-heading h2 { margin: 0 0 4px; font-size: 19px; }
.user-heading p,
.user-card small { margin: 0; color: var(--muted); }
.permission-list { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; }
.permission-list strong { width: 100%; color: var(--muted-strong); font-size: 12px; }
.user-permissions { margin: 0; }
.message { margin: 16px 0 0; font-weight: 650; }
.success { color: var(--success); }
.error { color: var(--danger); }
.muted { color: var(--muted); }
@media (max-width: 760px) { .user-grid { grid-template-columns: 1fr; } }
</style>
