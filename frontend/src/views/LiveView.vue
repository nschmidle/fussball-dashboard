<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">⚡ Live</h4>
      <div>
        <button class="btn btn-sm btn-outline-secondary me-2" @click="toggleNotify">
          {{ notifyEnabled ? '🔔 Benachrichtigungen an' : '🔕 Benachrichtigungen aus' }}
        </button>
        <small class="text-muted">alle 30s</small>
      </div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-auto" v-for="l in Object.keys(leagues)" :key="l">
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" :id="'league-'+l" v-model="leagues[l]" />
          <label class="form-check-label" :for="'league-'+l">{{ leagueNames[l] }}</label>
        </div>
      </div>
    </div>

    <div v-if="error" class="alert alert-warning">{{ error }}</div>

    <div v-if="!liveData.length" class="text-center py-5 text-muted">
      Keine Live-Daten – aktuell finden wohl keine Spiele statt.
    </div>

    <div class="row g-3" v-for="(group, idx) in groupedMatches" :key="idx">
      <div class="col-12">
        <h5 class="mt-2 mb-2">{{ group.league }}</h5>
      </div>
      <div class="col-md-6 col-lg-4" v-for="m in group.matches" :key="m.match_id">
        <div class="card match-card" :class="{ 'border-success': !m.finished && m.score1 != null }">
          <div class="card-body text-center">
            <small class="text-muted">{{ m.matchday }}</small>
            <div class="row align-items-center my-3">
              <div class="col-5 text-end fw-medium">{{ m.team1 }}</div>
              <div class="col-2">
                <span class="score fs-3" :class="{ 'score-live': !m.finished && m.score1 != null }">
                  {{ m.score1 != null ? m.score1 : '–' }}:{{ m.score2 != null ? m.score2 : '–' }}
                </span>
              </div>
              <div class="col-5 text-start fw-medium">{{ m.team2 }}</div>
            </div>
            <div v-if="m.finished" class="badge bg-secondary">beendet</div>
            <div v-else-if="m.score1 != null" class="badge bg-danger">LIVE</div>
            <div v-else class="badge bg-warning text-dark">ausstehend</div>

            <div v-if="m.goals.length" class="mt-2 border-top pt-2">
              <div v-for="g in m.goals" :key="g.goal_id" class="small">
                <span class="text-danger">⚽</span>
                {{ g.scorer }} ({{ g.minute }}')
                <span class="text-muted">– {{ g.score1 }}:{{ g.score2 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'

const liveData = ref([])
const error = ref('')
const notifyEnabled = ref(false)

const leagueNames = {
  bl1: '1. Bundesliga',
  bl2: '2. Bundesliga',
  dfb: 'DFB-Pokal',
  ucl: 'Champions League',
  uel: 'Europa League',
}
const leagues = reactive({
  bl1: true,
  bl2: true,
  dfb: true,
  ucl: true,
  uel: false,
})

let pollTimer = null
let knownGoals = new Set()

function loadKnownGoals() {
  try {
    const raw = localStorage.getItem('live_known_goals')
    if (raw) knownGoals = new Set(JSON.parse(raw))
  } catch {}
}

function saveKnownGoals() {
  localStorage.setItem('live_known_goals', JSON.stringify([...knownGoals]))
}

const groupedMatches = computed(() => {
  const active = Object.entries(leagues).filter(([, v]) => v).map(([k]) => k)
  const filtered = liveData.value.filter(m => active.includes(m.league_shortcut))
  const map = {}
  for (const m of filtered) {
    if (!map[m.league]) map[m.league] = { league: m.league, matches: [] }
    map[m.league].matches.push(m)
  }
  return Object.values(map)
})

async function poll() {
  try {
    const data = await api('/api/live')
    error.value = ''

    for (const m of data) {
      for (const g of m.goals) {
        if (!knownGoals.has(g.goal_id)) {
          knownGoals.add(g.goal_id)
          if (notifyEnabled.value && !m.finished) {
            showNotification(g, m)
          }
        }
      }
    }
    saveKnownGoals()
    liveData.value = data
  } catch (e) {
    error.value = 'Fehler beim Laden der Live-Daten'
  }
}

function showNotification(goal, match) {
  if (!('Notification' in window)) return
  if (Notification.permission === 'granted') {
    new Notification(`⚽ Goal! ${match.team1} ${match.score1}:${match.score2} ${match.team2}`, {
      body: `${goal.scorer} (${goal.minute}') – ${match.league}`,
      icon: '/favicon.ico',
    })
  }
}

function toggleNotify() {
  notifyEnabled.value = !notifyEnabled.value
  if (notifyEnabled.value && 'Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
}

onMounted(() => {
  loadKnownGoals()
  poll()
  pollTimer = setInterval(poll, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
