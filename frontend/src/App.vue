<template>
  <div>
    <nav class="navbar navbar-dark bg-dark mb-4">
      <div class="container position-relative">
        <div class="nav-left">
          <router-link class="navbar-brand" to="/">⚽ Fußball Dashboard</router-link>
          <div class="nav-version text-white-50">
            <div>Version: {{ version }}</div>
            <div>Build: {{ buildDate }}</div>
          </div>
        </div>
        <div class="nav-right d-flex align-items-center gap-2">
          <router-link class="nav-link text-nowrap" :class="{ 'active-link': isActive('/live') }" to="/live">⚡ Live</router-link>
          <button class="burger" :class="{ open }" type="button" @click="open = !open"
                  aria-label="Navigation umschalten" :aria-expanded="open">
            <span></span><span></span><span></span>
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

.burger {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: .45rem .35rem;
  background: transparent;
  border: none;
}

.burger span {
  width: 22px;
  height: 2px;
  border-radius: 1px;
  background: rgba(255, 255, 255, .8);
  transition: transform .2s ease, opacity .2s ease, background .15s ease;
}

.burger:hover span {
  background: #fff;
}

.burger.open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.burger.open span:nth-child(2) { opacity: 0; }
.burger.open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

.burger:focus-visible {
  outline: 2px solid rgba(255, 255, 255, .3);
  outline-offset: 2px;
}

.nav-link.active-link {
  color: #fff;
  font-weight: 600;
}

.nav-left {
  display: flex;
  flex-direction: column;
}

.nav-version {
  font-size: .72rem;
  line-height: 1.35;
}

@media (min-width: 768px) {
  .nav-version {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
  }
}
</style>
