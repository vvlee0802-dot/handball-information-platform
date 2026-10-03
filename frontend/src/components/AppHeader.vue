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
      <span class="brand-copy">
        <strong>手球数据平台</strong>
        <small>Handball Intelligence</small>
      </span>
    </RouterLink>

    <div class="header-actions">
      <nav class="primary-nav" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/competitions">赛事</RouterLink>
        <RouterLink to="/matches">比赛</RouterLink>
        <RouterLink to="/teams">球队</RouterLink>
        <RouterLink to="/players">球员</RouterLink>
        <RouterLink to="/venues">场馆</RouterLink>
        <RouterLink
          v-if="authStore.hasPermission('query_knowledge_base') || authStore.hasPermission('manage_knowledge_base')"
          to="/knowledge"
        >
          知识库
        </RouterLink>
        <RouterLink v-if="authStore.hasPermission('use_match_agent')" to="/agent">分析 Agent</RouterLink>
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
  min-height: 76px;
  padding: 0 max(28px, calc((100vw - 1360px) / 2));
  border-bottom: 0;
  color: white;
  background: rgba(7, 26, 47, 0.98);
  box-shadow: 0 8px 30px rgba(7, 26, 47, 0.12);
  backdrop-filter: blur(16px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: white;
}

.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 11px;
  color: white;
  background: var(--primary);
  font-size: 14px;
  font-weight: 700;
}

.brand-copy { display: grid; gap: 1px; }
.brand strong { font-size: 15px; font-weight: 700; }
.brand small { color: #9eafc5; font-size: 9px; letter-spacing: .03em; }

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
.account-area { gap: 9px; padding-left: 16px; border-left: 1px solid rgba(255, 255, 255, 0.13); }
.session-status { color: #9eafc5; font-size: 12px; }
.user-name { max-width: 120px; overflow: hidden; font-size: 13px; font-weight: 720; text-overflow: ellipsis; white-space: nowrap; }
.account-button {
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 11px;
  color: white;
  background: #12375f;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
.account-button:hover { border-color: rgba(255, 255, 255, 0.28); background: #194875; }
.login-link { display: inline-flex; align-items: center; color: white; }

.primary-nav a {
  padding: 27px 10px 23px;
  border-bottom: 3px solid transparent;
  color: #aebbd0;
  font-size: 14px;
  font-weight: 650;
}

.primary-nav a:hover,
.primary-nav a.router-link-active {
  color: white;
  border-bottom-color: var(--primary);
}

@media (max-width: 760px) {
  .app-header { flex-wrap: wrap; align-items: center; gap: 12px; min-height: 64px; padding: 12px 16px; }
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
