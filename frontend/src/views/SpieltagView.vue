<template>
  <div>
    <div v-if="loaded && !groups.length" class="text-center py-5 text-muted">
      Heute finden keine Spiele statt.
    </div>

    <div class="card mb-3" v-for="g in groups" :key="g.league_shortcut">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span>{{ g.league_name }}</span>
        <span class="badge bg-secondary">{{ g.matches.length }} Spiele</span>
      </div>
      <div class="table-responsive">
        <table class="table table-sm align-middle mb-0 spieltag-table">
          <tbody>
            <tr v-for="m in g.matches" :key="m.id">
              <td class="text-nowrap">
                {{ formatTime(m.date) }}
                <span v-if="isLive(m)" class="live-dot" title="läuft gerade"></span>
              </td>
              <td class="text-end">{{ m.team1 }}</td>
              <td class="text-center score-cell" :class="{ 'score-live': isLive(m) }">
                {{ m.score1 != null ? m.score1 : '–' }}:{{ m.score2 != null ? m.score2 : '–' }}
              </td>
              <td>{{ m.team2 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <details class="card mt-3">
      <summary class="card-header d-flex justify-content-between align-items-center" style="cursor:pointer">
        <span>Scrape-Historie</span>
        <span class="badge bg-secondary">{{ history.length }}/20</span>
      </summary>
      <div v-if="!history.length" class="card-body text-muted small">
        Noch keine Scrape-Läufe seit Serverstart.
      </div>
      <div v-else class="table-responsive">
        <table class="table table-sm mb-0 spieltag-table">
          <tbody>
            <tr v-for="(h, i) in history" :key="i">
              <td class="text-nowrap">{{ formatTs(h.ts) }}</td>
              <td><span class="badge" :class="h.trigger === 'live' ? 'bg-danger' : 'bg-secondary'">{{ h.trigger }}</span></td>
              <td class="text-nowrap text-end pe-3">{{ h.duration_s }} s</td>
              <template v-if="h.error">
                <td colspan="2" class="text-danger">Fehler: {{ h.error }}</td>
              </template>
              <template v-else>
                <td>{{ h.total }} Spiele</td>
                <td :class="h.updated ? 'text-success fw-bold' : ''">Δ {{ h.updated }}</td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'

const POLL_MS = 5000

const groups = ref([])
const history = ref([])
const loaded = ref(false)
const now = ref(new Date())
let pollTimer = null

onMounted(async () => {
  await refresh()
  pollTimer = setInterval(tick, POLL_MS)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function refresh() {
  try {
    const [g, h] = await Promise.all([
      api('/api/spieltag'),
      api('/api/scrape-history'),
    ])
    groups.value = g
    history.value = h
  } catch {}
  loaded.value = true
}

async function tick() {
  now.value = new Date()
  if (document.hidden || !anyLive()) return
  await refresh()
}

function anyLive() {
  return groups.value.some(g => g.matches.some(isLive))
}

function formatTime(d) {
  if (!d) return ''
  return new Date(d).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

function formatTs(d) {
  if (!d) return ''
  return new Date(d).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function isLive(m) {
  return !m.finished && new Date(m.date) <= now.value
}
</script>

<style scoped>
.spieltag-table {
  font-size: .85rem;
}

.spieltag-table td,
.spieltag-table th {
  vertical-align: middle;
}

.score-cell {
  min-width: 3.5rem;
  font-variant-numeric: tabular-nums;
}

.score-live {
  color: #dc3545;
  font-weight: 700;
}

.live-dot {
  display: inline-block;
  width: .5rem;
  height: .5rem;
  margin-left: .35rem;
  border-radius: 50%;
  background-color: #198754;
  animation: live-pulse 1.2s ease-in-out infinite;
}

@keyframes live-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .3; }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
}
</style>
