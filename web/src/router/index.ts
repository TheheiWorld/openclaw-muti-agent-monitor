import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Instances from '../views/Instances.vue'
import InstanceDetail from '../views/InstanceDetail.vue'
import Agents from '../views/Agents.vue'
import AgentDetail from '../views/AgentDetail.vue'
import Ranks from '../views/Ranks.vue'
import TokenStats from '../views/TokenStats.vue'
import Login from '../views/Login.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login, meta: { public: true } },
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/instances', name: 'Instances', component: Instances },
  { path: '/instances/:id', name: 'InstanceDetail', component: InstanceDetail },
  { path: '/agents', name: 'Agents', component: Agents },
  { path: '/agents/:id', name: 'AgentDetail', component: AgentDetail },
  { path: '/ranks', name: 'Ranks', component: Ranks },
  { path: '/tokens', name: 'TokenStats', component: TokenStats },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) {
    // Already logged in, redirect away from login page
    if (token && to.name === 'Login') {
      next({ name: 'Dashboard' })
    } else {
      next()
    }
  } else {
    // Protected route
    if (!token) {
      next({ name: 'Login' })
    } else {
      next()
    }
  }
})

export default router
