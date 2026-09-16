<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ email: '', password: '' })
const isSubmitting = ref(false)
const errorMessage = ref('')

const handleSubmit = async () => {
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    await authStore.login(form)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch {
    errorMessage.value = '邮箱或密码错误，请重新输入。'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="page-shell login-page">
    <AppHeader />
    <main class="login-container">
      <section class="login-card" aria-labelledby="login-title">
        <div>
          <p class="eyebrow">Account</p>
          <h1 id="login-title">登录平台</h1>
          <p class="login-description">登录后可以创建和维护赛事基础数据。</p>
        </div>

        <form class="login-form" @submit.prevent="handleSubmit">
          <div class="field">
            <label for="login-email">邮箱</label>
            <input
              id="login-email"
              v-model.trim="form.email"
              type="email"
              autocomplete="username"
              required
              maxlength="254"
              placeholder="coach@example.com"
            />
          </div>

          <div class="field">
            <label for="login-password">密码</label>
            <input
              id="login-password"
              v-model="form.password"
              type="password"
              autocomplete="current-password"
              required
              maxlength="128"
              placeholder="请输入密码"
            />
          </div>

          <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>

          <button class="button button-primary login-button" type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? '登录中…' : '登录' }}
          </button>
        </form>
      </section>
    </main>
  </div>
</template>

<style scoped>
.login-page {
  background:
    radial-gradient(circle at 18% 12%, #e8efff 0, transparent 32%),
    var(--surface-soft);
}

.login-container {
  display: grid;
  min-height: calc(100vh - 73px);
  padding: 48px 20px;
  place-items: center;
}

.login-card {
  width: min(100%, 440px);
  padding: 36px;
  border: 1px solid var(--border);
  border-radius: 22px;
  background: white;
  box-shadow: 0 24px 70px rgba(31, 45, 80, 0.12);
}

.login-card h1 { margin: 0; font-size: 34px; letter-spacing: -0.03em; }
.login-description { margin: 10px 0 0; color: var(--muted-strong); }
.login-form { display: grid; gap: 18px; margin-top: 30px; }
.login-button { width: 100%; margin-top: 4px; }
.form-error { margin: 0; color: var(--danger); font-size: 14px; }

@media (max-width: 520px) {
  .login-container { align-items: start; padding-top: 32px; }
  .login-card { padding: 26px 22px; }
}
</style>
