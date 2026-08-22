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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'

const POLL_MS = 5000

const groups = ref([])
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
    groups.value = await api('/api/spieltag')
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
