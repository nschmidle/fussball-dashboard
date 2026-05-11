import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'

import Dashboard from './views/Dashboard.vue'
import MatchesView from './views/MatchesView.vue'
import StandingsView from './views/StandingsView.vue'
import StatsView from './views/StatsView.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/matches', component: MatchesView },
  { path: '/standings', component: StandingsView },
  { path: '/stats', component: StatsView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

createApp(App).use(router).mount('#app')
