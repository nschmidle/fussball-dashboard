<template>
  <div>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
      <div class="container">
        <router-link class="navbar-brand" to="/">
          ⚽ Fußball Dashboard
          <span class="d-block text-white-50" style="font-size:0.72rem; line-height:1.1;">
            v{{ version }} · Build: {{ buildDate }}
          </span>
        </router-link>
        <button class="navbar-toggler" type="button" @click="open = !open"
                aria-label="Navigation umschalten" :aria-expanded="open">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" :class="{ show: open }">
          <div class="navbar-nav">
            <router-link class="nav-link" to="/">Dashboard</router-link>
            <router-link class="nav-link" to="/matches">Spiele</router-link>
            <router-link class="nav-link" to="/standings">Tabelle</router-link>
            <router-link class="nav-link" to="/stats">Statistiken</router-link>
            <router-link class="nav-link" to="/live">⚡ Live</router-link>
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
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api.js'

const route = useRoute()
const open = ref(false)
const version = ref('?')
const buildDate = ref('dev')

watch(() => route.path, () => { open.value = false })

onMounted(loadVersion)

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
