import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const authStore = useAuthStore(pinia)

window.addEventListener('auth:unauthorized', () => {
  authStore.clearSession()
  if (router.currentRoute.value.name !== 'login') {
    void router.push({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  }
})

void authStore.restoreSession().catch(() => undefined)

app.mount('#app')
