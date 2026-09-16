<script setup lang="ts">
defineProps<{ entity: string }>()
</script>

<template>
  <div class="detail-card empty-state">
    <h1>未找到{{ entity }}</h1>
    <p>该记录可能不存在，或链接已经失效。</p>
    <RouterLink class="button button-primary" to="/">返回首页</RouterLink>
  </div>
</template>

<style scoped>
h1 { margin: 0 0 8px; font-size: 28px; }
p { margin: 0 0 22px; }
</style>
