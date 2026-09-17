<script setup lang="ts">
import { RouterLink, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const handleLogout = async () => {
  await authStore.logout()
  await router.push('/')
}
</script>

<template>
  <header class="app-header">
    <RouterLink class="brand" to="/" aria-label="返回首页">
      <span class="brand-mark">H</span>
      <span>
        <strong>手球数据平台</strong>
        <small>Handball Intelligence</small>
      </span>
    </RouterLink>

    <div class="header-actions">
      <nav class="primary-nav" aria-label="主导航">
        <RouterLink to="/competitions">赛事</RouterLink>
        <RouterLink to="/matches">比赛</RouterLink>
        <RouterLink to="/teams">球队</RouterLink>
        <RouterLink to="/players">球员</RouterLink>
        <RouterLink to="/venues">场馆</RouterLink>
        <RouterLink v-if="authStore.hasPermission('manage_users')" to="/admin/users">
          用户管理
        </RouterLink>
      </nav>

      <div class="account-area">
        <span v-if="!authStore.initialized" class="session-status">检查会话…</span>
        <template v-else-if="authStore.user">
          <span class="user-name" :title="authStore.user.email">{{ authStore.user.display_name }}</span>
          <button class="account-button" type="button" @click="handleLogout">退出</button>
        </template>
        <RouterLink v-else class="account-button login-link" to="/login">登录</RouterLink>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 72px;
  padding: 0 5vw;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(16px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--ink);
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 12px;
  color: white;
  background: var(--primary);
  font-weight: 800;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong { font-size: 15px; }
.brand small { margin-top: 2px; color: var(--muted); font-size: 10px; letter-spacing: .08em; }

.primary-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.header-actions,
.account-area {
  display: flex;
  align-items: center;
}

.header-actions { gap: 18px; }
.account-area { gap: 9px; padding-left: 16px; border-left: 1px solid var(--border); }
.session-status { color: var(--muted); font-size: 12px; }
.user-name { max-width: 120px; overflow: hidden; font-size: 13px; font-weight: 720; text-overflow: ellipsis; white-space: nowrap; }
.account-button {
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 9px;
  color: var(--muted-strong);
  background: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
.account-button:hover { border-color: #bcc6d8; background: var(--surface-soft); }
.login-link { display: inline-flex; align-items: center; color: var(--primary-dark); }

.primary-nav a {
  padding: 9px 13px;
  border-radius: 10px;
  color: var(--muted-strong);
  font-size: 14px;
  font-weight: 650;
}

.primary-nav a:hover,
.primary-nav a.router-link-active {
  color: var(--primary-dark);
  background: var(--primary-soft);
}

@media (max-width: 760px) {
  .app-header { flex-wrap: wrap; align-items: center; gap: 12px; padding: 14px 20px; }
  .brand small { display: none; }
  .header-actions {
    width: 100%;
    max-width: none;
    justify-content: space-between;
    gap: 10px;
  }
  .primary-nav { max-width: calc(100% - 62px); overflow-x: auto; }
  .primary-nav a { padding: 8px 10px; white-space: nowrap; }
  .account-area { border-left: 0; padding-left: 0; }
}
</style>
