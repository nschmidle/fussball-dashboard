<template>
  <div>
    <div class="filter-bar mb-3 p-3 bg-white rounded shadow-sm">
      <select v-model="league" class="form-select form-select-sm" style="width:auto" @change="load">
        <option v-for="l in leagues" :key="l.league_shortcut" :value="l.league_shortcut">
          {{ l.league_name }}
        </option>
      </select>
    </div>

    <div class="card" v-if="standings.length">
      <table class="table table-hover mb-0">
        <thead class="table-dark">
          <tr>
            <th>#</th><th>Team</th><th>SP</th><th>S</th><th>U</th><th>N</th>
            <th>Tore</th><th>TD</th><th>Pkt</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in standings" :key="t.team">
            <td class="fw-bold text-muted">{{ t.pos }}</td>
            <td class="fw-medium">{{ t.team }}</td>
            <td>{{ t.played }}</td>
            <td>{{ t.wins }}</td>
            <td>{{ t.draws }}</td>
            <td>{{ t.losses }}</td>
            <td>{{ t.goals_for }}:{{ t.goals_against }}</td>
            <td>{{ t.gd > 0 ? '+' : '' }}{{ t.gd }}</td>
            <td><strong>{{ t.points }}</strong></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="text-center py-4 text-muted">Keine Daten</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const leagues = ref([])
const standings = ref([])
const league = ref('bl1')

onMounted(async () => {
  leagues.value = await api('/api/leagues')
  await load()
})

async function load() {
  standings.value = await api(`/api/standings?league=${league.value}`)
}
</script>
