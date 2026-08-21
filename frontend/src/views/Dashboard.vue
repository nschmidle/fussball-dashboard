<template>
  <div>
    <div class="row g-3 mb-4">
      <div class="col-md-3" v-for="s in statCards" :key="s.label">
        <div class="card stat-card text-center p-3">
          <div class="stat-number">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-6 col-lg-4" v-for="l in leagues" :key="l.league_shortcut">
        <div class="card" @click="$router.push('/standings')" style="cursor:pointer">
          <div class="card-header d-flex justify-content-between align-items-center">
            <span>{{ l.league_name }}</span>
            <span class="badge bg-secondary">{{ l.total }} Spiele</span>
          </div>
          <div class="card-body">
            <div class="d-flex justify-content-between mb-1">
              <small>{{ l.finished }} beendet</small>
              <small>{{ l.total - l.finished }} ausstehend</small>
            </div>
            <div class="progress" style="height:6px">
              <div class="progress-bar bg-success" :style="{ width: pct(l) + '%' }"></div>
            </div>
            <small class="text-muted mt-2 d-block">Saison {{ l.season }}/{{ l.season + 1 }}</small>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">Letzte Spiele</div>
      <div class="card-body p-0">
        <div v-for="m in recent" :key="m.id" class="match-row d-flex align-items-center py-2 px-3 border-bottom">
          <small class="text-muted me-3" style="min-width:120px">{{ formatDate(m.date) }}</small>
          <small class="text-muted me-3" style="min-width:100px">{{ m.matchday }}</small>
          <div class="flex-grow-1 text-end team-name pe-2" style="min-width:140px">{{ m.team1 }}</div>
          <div class="score mx-3 text-center" style="min-width:48px"
               :class="{ 'score-live': !m.finished && m.score1 != null }">
            {{ m.score1 != null ? m.score1 : '–' }}:{{ m.score2 != null ? m.score2 : '–' }}
          </div>
          <div class="flex-grow-1 text-start team-name ps-2" style="min-width:140px">{{ m.team2 }}</div>
          <span v-if="!m.finished" class="badge bg-danger ms-2">LIVE</span>
        </div>
      </div>
    </div>

    <div class="text-center text-muted small mt-4 mb-2">
      Fußball Dashboard v{{ version }} · Build: {{ buildDate }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const leagues = ref([])
const recent = ref([])
const version = ref('')
const buildDate = ref('')

const statCards = ref([])

onMounted(async () => {
  leagues.value = await api('/api/leagues')
  recent.value = await api('/api/matches?limit=20')
  loadVersion()

  const total = leagues.value.reduce((s, l) => s + l.total, 0)
  const finished = leagues.value.reduce((s, l) => s + l.finished, 0)
  statCards.value = [
    { value: total, label: 'Spiele gesamt' },
    { value: finished, label: 'beendet' },
    { value: total - finished, label: 'ausstehend' },
    { value: leagues.value.length, label: 'Ligen' },
  ]
})

async function loadVersion() {
  try {
    const v = await api('/api/version')
    version.value = v.version
    if (v.build_date && v.build_date !== 'dev') {
      const dt = new Date(v.build_date)
      buildDate.value = dt.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
        ' ' + dt.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) + ' UTC'
    } else {
      buildDate.value = 'dev'
    }
  } catch {
    version.value = '?'
    buildDate.value = '?'
  }
}

function pct(l) {
  return l.total ? Math.round(l.finished / l.total * 100) : 0
}

function formatDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  return dt.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) +
    ' ' + dt.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}
</script>
