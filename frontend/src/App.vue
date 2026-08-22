<template>
  <div>
    <nav class="navbar navbar-dark bg-dark mb-4">
      <div class="container position-relative">
        <router-link class="navbar-brand" to="/">
          ⚽ Fußball Dashboard
          <span class="d-block text-white-50" style="font-size:0.72rem; line-height:1.1;">
            v{{ version }} · Build: {{ buildDate }}
          </span>
        </router-link>
        <div class="nav-right d-flex align-items-center gap-2">
          <router-link class="nav-link text-nowrap" :class="{ 'active-link': isActive('/live') }" to="/live">⚡ Live</router-link>
          <button class="navbar-toggler" type="button" @click="open = !open"
                  aria-label="Navigation umschalten" :aria-expanded="open">
            <span class="navbar-toggler-icon"></span>
          </button>
        </div>
        <div class="collapse nav-panel" :class="{ show: open }">
          <div class="navbar-nav">
            <router-link class="nav-link" :class="{ 'active-link': isActive('/') }" to="/">Dashboard</router-link>
            <router-link class="nav-link" :class="{ 'active-link': isActive('/matches') }" to="/matches">Spiele</router-link>
            <router-link class="nav-link" :class="{ 'active-link': isActive('/standings') }" to="/standings">Tabelle</router-link>
            <router-link class="nav-link" :class="{ 'active-link': isActive('/stats') }" to="/stats">Statistiken</router-link>
          </div>
        </div>
      </div>
    </nav>
    <div class="container">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api.js'

const route = useRoute()
const open = ref(false)
const version = ref('?')
const buildDate = ref('dev')

watch(() => route.path, () => { open.value = false })

onMounted(() => {
  loadVersion()
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
})

function isActive(path) {
  return route.path === path
}

function onDocClick(e) {
  const t = e.target
  if (t instanceof Element && (t.closest('.nav-right') || t.closest('.nav-panel'))) return
  open.value = false
}

async function loadVersion() {
  try {
    const v = await api('/api/version')
    version.value = v.version
    buildDate.value = formatBuildDate(v.build_date)
  } catch {
    version.value = '?'
    buildDate.value = '?'
  }
}

function formatBuildDate(d) {
  if (!d || d === 'dev') return 'dev'
  const dt = new Date(d)
  return dt.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' + dt.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) + ' UTC'
}
</script>

<style scoped>
.nav-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 1030;
  min-width: 220px;
  background: var(--bs-dark);
  border: 1px solid rgba(255, 255, 255, .15);
  border-radius: .5rem;
  box-shadow: 0 .5rem 1rem rgba(0, 0, 0, .5);
}

.nav-panel .navbar-nav {
  padding: .5rem 0;
}

.nav-panel .nav-link {
  padding: .45rem 1.25rem;
}

.nav-right .nav-link {
  color: rgba(255, 255, 255, .8);
}

.nav-right .nav-link:hover {
  color: #fff;
}

.nav-link.active-link {
  color: #fff;
  font-weight: 600;
}
</style>
