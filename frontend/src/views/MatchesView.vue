<template>
  <div>
    <div class="filter-bar d-flex flex-wrap align-items-center gap-2 mb-3 p-3 bg-white rounded shadow-sm">
      <select v-model="league" class="form-select form-select-sm" style="width:auto" @change="onLeagueChange">
        <option v-for="l in leagues" :key="l.league_shortcut" :value="l.league_shortcut">
          {{ l.league_name }}
        </option>
      </select>
      <select v-model="matchday" class="form-select form-select-sm" style="width:auto">
        <option value="">Alle Spieltage</option>
        <option v-for="md in matchdays" :key="md" :value="md">{{ md }}</option>
      </select>
      <input v-model="team" class="form-control form-control-sm" placeholder="Team suchen..." style="width:160px" />
      <button class="btn btn-sm btn-primary" @click="load">Filtern</button>
    </div>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4 text-muted">Lade...</div>
        <div v-else-if="!matches.length" class="text-center py-4 text-muted">Keine Spiele gefunden</div>
        <div v-for="m in matches" :key="m.id" class="match-row d-flex align-items-center py-2 px-3 border-bottom">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const leagues = ref([])
const matchdays = ref([])
const matches = ref([])
const loading = ref(false)

const league = ref('bl1')
const matchday = ref('')
const team = ref('')

onMounted(async () => {
  leagues.value = await api('/api/leagues')
  await onLeagueChange()
})

async function onLeagueChange() {
  matchday.value = ''
  matchdays.value = await api(`/api/matchdays?league=${league.value}`)
  await load()
}

async function load() {
  loading.value = true
  let url = `/api/matches?league=${league.value}&limit=500`
  if (matchday.value) url += `&matchday=${encodeURIComponent(matchday.value)}`
  if (team.value) url += `&team=${encodeURIComponent(team.value)}`
  matches.value = await api(url)
  loading.value = false
}

function formatDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  return dt.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) +
    ' ' + dt.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}
</script>
