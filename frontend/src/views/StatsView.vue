<template>
  <div>
    <div class="filter-bar mb-3 p-3 bg-white rounded shadow-sm">
      <select v-model="league" class="form-select form-select-sm" style="width:auto" @change="load">
        <option v-for="l in leagues" :key="l.league_shortcut" :value="l.league_shortcut">
          {{ l.league_name }}
        </option>
      </select>
    </div>

    <div v-if="data" class="row g-3 mb-3">
      <div class="col-md-4">
        <div class="card stat-card text-center p-3">
          <div class="stat-number">{{ data.result_distribution.avg_goals }}</div>
          <div class="stat-label">Ø Tore/Spiel</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card stat-card text-center p-3">
          <div class="stat-number">{{ data.result_distribution.home_wins }}</div>
          <div class="stat-label">Heimsiege</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card stat-card text-center p-3">
          <div class="stat-number">{{ data.result_distribution.away_wins }}</div>
          <div class="stat-label">Auswärtssiege</div>
        </div>
      </div>
    </div>

    <div class="row g-3" v-if="data">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">Tore pro Spieltag</div>
          <div class="card-body">
            <div class="chart-container" style="position:relative; height:300px">
              <Bar v-if="data.goals_per_matchday.length" :data="barData" :options="barOptions" />
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">Ergebnisverteilung</div>
          <div class="card-body">
            <div class="chart-container" style="position:relative; height:300px">
              <Doughnut :data="doughnutData" :options="doughnutOptions" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card mt-3" v-if="data && data.top_scorers.length">
      <div class="card-header">Top-Torjäger</div>
      <div class="card-body p-0">
        <table class="table table-hover mb-0">
          <thead>
            <tr><th>#</th><th>Spieler</th><th>Tore</th></tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in data.top_scorers.slice(0, 10)" :key="s.scorer">
              <td>{{ i + 1 }}</td>
              <td>{{ s.scorer }}</td>
              <td><strong>{{ s.goals }}</strong></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend } from 'chart.js'
import { api } from '../api.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend)

const leagues = ref([])
const data = ref(null)
const league = ref('bl1')

onMounted(async () => {
  leagues.value = await api('/api/leagues')
  await load()
})

async function load() {
  data.value = await api(`/api/stats?league=${league.value}`)
}

const barData = computed(() => ({
  labels: data.value?.goals_per_matchday.map(g => g.matchday.replace(' Spieltag', '.')) || [],
  datasets: [{
    label: 'Tore',
    data: data.value?.goals_per_matchday.map(g => g.goals) || [],
    backgroundColor: 'rgba(13,110,253,.6)',
    borderColor: '#0d6efd',
    borderWidth: 1,
  }],
}))

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { y: { beginAtZero: true, ticks: { stepSize: 5 } } },
}

const doughnutData = computed(() => ({
  labels: ['Heimsieg', 'Unentschieden', 'Auswärtssieg'],
  datasets: [{
    data: [
      data.value?.result_distribution.home_wins || 0,
      data.value?.result_distribution.draws || 0,
      data.value?.result_distribution.away_wins || 0,
    ],
    backgroundColor: ['#198754', '#ffc107', '#dc3545'],
  }],
}))

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'bottom' } },
}
</script>
