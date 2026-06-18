import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import Dashboard from './views/Dashboard.vue'
import Top100 from './views/Top100.vue'
import LimitUp from './views/LimitUp.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/top100', component: Top100 },
  { path: '/limit-up', component: LimitUp },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
