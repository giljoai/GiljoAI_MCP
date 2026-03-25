<template>
  <div class="donut-chart-wrapper">
    <div class="text-caption text-medium-emphasis mb-2">{{ title }}</div>
    <div class="donut-chart-container">
      <Doughnut
        v-if="hasData"
        :key="dataHash"
        :data="formattedData"
        :options="chartOptions"
      />
      <div v-else class="no-data-placeholder d-flex align-center justify-center">
        <span class="text-caption text-disabled">No data</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Doughnut } from 'vue-chartjs'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  title: {
    type: String,
    default: '',
  },
  chartData: {
    type: Object,
    default: () => ({ labels: [], values: [], colors: [] }),
  },
})

const hasData = computed(() => {
  return props.chartData.values && props.chartData.values.some((v) => v > 0)
})

const dataHash = computed(() => {
  if (!props.chartData.values) return '0'
  return `${props.chartData.labels.join(',')}:${props.chartData.values.join(',')}`
})

const formattedData = computed(() => ({
  labels: props.chartData.labels || [],
  datasets: [
    {
      data: props.chartData.values || [],
      backgroundColor: props.chartData.colors || [],
      borderColor: 'rgba(0, 0, 0, 0.3)',
      borderWidth: 1,
      hoverBorderColor: '#FFD700',
      hoverBorderWidth: 2,
    },
  ],
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  cutout: '55%',
  animation: {
    animateRotate: true,
    duration: 1000,
  },
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        color: 'rgba(255, 255, 255, 0.7)',
        font: {
          size: 11,
          family: 'Roboto, sans-serif',
        },
        padding: 10,
        usePointStyle: true,
        pointStyle: 'circle',
        boxWidth: 8,
      },
    },
    tooltip: {
      backgroundColor: '#1e3147',
      titleColor: '#FFD700',
      bodyColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: 'rgba(255, 215, 0, 0.3)',
      borderWidth: 1,
      padding: 10,
      callbacks: {
        label: (context) => {
          const total = context.dataset.data.reduce((a, b) => a + b, 0)
          const value = context.raw
          const pct = total > 0 ? Math.round((value / total) * 100) : 0
          return ` ${context.label}: ${value} (${pct}%)`
        },
      },
    },
  },
}))
</script>

<style scoped>
.donut-chart-wrapper {
  text-align: center;
}

.donut-chart-container {
  width: 200px;
  height: 200px;
  margin: 0 auto;
}

.no-data-placeholder {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 2px dashed rgba(255, 255, 255, 0.15);
  margin: 0 auto;
}
</style>
