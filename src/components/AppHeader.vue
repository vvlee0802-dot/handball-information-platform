<script setup lang="ts">
import { RouterLink } from 'vue-router'
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

    <nav class="primary-nav" aria-label="主导航">
      <RouterLink to="/competitions">赛事</RouterLink>
      <RouterLink to="/matches">比赛</RouterLink>
      <RouterLink to="/teams">球队</RouterLink>
      <RouterLink to="/players">球员</RouterLink>
      <RouterLink to="/venues">场馆</RouterLink>
    </nav>
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
  .app-header { align-items: flex-start; padding: 14px 20px; }
  .brand small { display: none; }
  .primary-nav { max-width: 64vw; overflow-x: auto; }
  .primary-nav a { padding: 8px 10px; white-space: nowrap; }
}
</style>
