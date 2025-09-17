<template>
  <v-card class="agent-metrics" elevation="2">
    <v-card-title>
      <v-icon class="mr-2" color="primary">
        <img src="/icons/chart.svg" width="24" height="24" alt="Metrics" />
      </v-icon>
      <span>Agent Performance Metrics</span>
      <v-spacer />
      <v-btn icon="mdi-refresh" size="small" @click="refreshMetrics" />
    </v-card-title>

    <v-card-text>
      <v-row>
        <!-- Summary Cards -->
        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-caption">Total Agents</div>
              <div class="text-h4">{{ metrics?.agent_counts?.total || 0 }}</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-caption">Active</div>
              <div class="text-h4 text-success">{{ metrics?.agent_counts?.active || 0 }}</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-caption">Completed</div>
              <div class="text-h4 text-grey">{{ metrics?.agent_counts?.completed || 0 }}</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-caption">Avg Context</div>
              <div class="text-h4">{{ formatContext(metrics?.average_context_usage) }}</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charts -->
      <v-row class="mt-4">
        <v-col cols="12" md="6">
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1">Agent Distribution by Role</v-card-title>
            <v-card-text>
              <canvas ref="roleChart" height="200"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1">Hourly Activity</v-card-title>
            <v-card-text>
              <canvas ref="activityChart" height="200"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Top Token Users -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-1">Top Token Usage</v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item
                  v-for="agent in metrics?.top_token_usage || []"
                  :key="agent.agent_name"
                >
                  <v-list-item-title>{{ agent.agent_name }}</v-list-item-title>
                  <template v-slot:append>
                    <v-chip size="small">{{ formatTokens(agent.context_used) }}</v-chip>
                  </template>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import api from '@/services/api'

Chart.register(...registerables)

const props = defineProps({
  projectId: {
    type: String,
    default: null,
  },
  metrics: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['refresh'])

// Refs
const roleChart = ref(null)
const activityChart = ref(null)
let roleChartInstance = null
let activityChartInstance = null

// Methods
const formatContext = (value) => {
  if (!value) return '0'
  return `${Math.round(value / 1000)}K`
}

const formatTokens = (value) => {
  if (!value) return '0'
  if (value > 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value > 1000) return `${(value / 1000).toFixed(1)}K`
  return value.toString()
}

const refreshMetrics = () => {
  emit('refresh')
}

const createRoleChart = () => {
  if (!props.metrics?.agent_distribution_by_role) return

  const ctx = roleChart.value?.getContext('2d')
  if (!ctx) return

  if (roleChartInstance) {
    roleChartInstance.destroy()
  }

  const data = props.metrics.agent_distribution_by_role
  roleChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: Object.keys(data),
      datasets: [
        {
          data: Object.values(data),
          backgroundColor: ['#67bd6d', '#ffc300', '#8b5cf6', '#c6298c', '#8f97b7'],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#e1e1e1',
          },
        },
      },
    },
  })
}

const createActivityChart = () => {
  if (!props.metrics?.hourly_activity) return

  const ctx = activityChart.value?.getContext('2d')
  if (!ctx) return

  if (activityChartInstance) {
    activityChartInstance.destroy()
  }

  const data = props.metrics.hourly_activity
  activityChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Object.keys(data).map((h) => `${h}:00`),
      datasets: [
        {
          label: 'Agent Activity',
          data: Object.values(data),
          borderColor: '#ffc300',
          backgroundColor: 'rgba(255, 195, 0, 0.1)',
          tension: 0.4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        x: {
          grid: {
            color: '#315074',
          },
          ticks: {
            color: '#8f97b7',
          },
        },
        y: {
          grid: {
            color: '#315074',
          },
          ticks: {
            color: '#8f97b7',
          },
        },
      },
    },
  })
}

// Lifecycle
onMounted(() => {
  if (props.metrics) {
    createRoleChart()
    createActivityChart()
  }
})

// Watch for metrics changes
watch(
  () => props.metrics,
  () => {
    createRoleChart()
    createActivityChart()
  },
  { deep: true },
)
</script>

<style scoped lang="scss">
.agent-metrics {
  background: #1e3147;

  :deep(.v-card) {
    background: #182739;
  }

  :deep(.v-card-text) {
    color: #e1e1e1;
  }

  :deep(.v-list-item-title) {
    color: #e1e1e1;
  }
}
</style>
