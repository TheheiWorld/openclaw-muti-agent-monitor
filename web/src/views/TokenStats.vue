<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getTokenSummary, getTokenTrend } from '../api'
import { useI18n } from '../i18n'
import TokenChart from '../components/TokenChart.vue'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, TitleComponent, TooltipComponent, GridComponent])

const { t } = useI18n()
const loading = ref(true)
const timeRange = ref('24h')
const summary = ref<any>({
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_tokens: 0,
  by_instance: [],
  by_agent: [],
})
const trend = ref<any[]>([])

const timeRangeKeys = [
  { value: '24h', key: 'tokenStats.range24h' },
  { value: '7d', key: 'tokenStats.range7d' },
  { value: '30d', key: 'tokenStats.range30d' },
]

const formatTokens = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

const fetchData = async () => {
  loading.value = true
  try {
    const [summaryRes, trendRes] = await Promise.all([
      getTokenSummary(),
      getTokenTrend({ range: timeRange.value }),
    ])
    summary.value = summaryRes.data
    trend.value = trendRes.data.points
  } catch (e) {
    console.error('Failed to load token stats', e)
  } finally {
    loading.value = false
  }
}

const instanceBarOption = () => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#FFFFFF',
    borderColor: '#1A1A1A',
    borderWidth: 2,
    textStyle: { color: '#1A1A1A', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 },
  },
  grid: { left: 120, right: 16, top: 8, bottom: 24 },
  xAxis: {
    type: 'value',
    axisLabel: { formatter: (v: number) => formatTokens(v), color: '#888', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#E5E1DB', type: 'dashed' } },
  },
  yAxis: {
    type: 'category',
    data: summary.value.by_instance.map((i: any) => i.instance_name).reverse(),
    axisLabel: { fontSize: 11, color: '#555', fontFamily: 'JetBrains Mono, monospace' },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  series: [{
    type: 'bar',
    data: summary.value.by_instance.map((i: any) => i.total_tokens).reverse(),
    itemStyle: { color: '#D71921', borderRadius: 0 },
    barMaxWidth: 20,
  }],
})

const agentBarOption = () => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#FFFFFF',
    borderColor: '#1A1A1A',
    borderWidth: 2,
    textStyle: { color: '#1A1A1A', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 },
  },
  grid: { left: 100, right: 16, top: 8, bottom: 24 },
  xAxis: {
    type: 'value',
    axisLabel: { formatter: (v: number) => formatTokens(v), color: '#888', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#E5E1DB', type: 'dashed' } },
  },
  yAxis: {
    type: 'category',
    data: summary.value.by_agent.slice(0, 10).map((a: any) => a.agent_id).reverse(),
    axisLabel: { fontSize: 11, color: '#555', fontFamily: 'JetBrains Mono, monospace' },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  series: [{
    type: 'bar',
    data: summary.value.by_agent.slice(0, 10).map((a: any) => a.total_tokens).reverse(),
    itemStyle: { color: '#1A1A1A', borderRadius: 0 },
    barMaxWidth: 20,
  }],
})

onMounted(fetchData)
watch(timeRange, fetchData)
</script>

<template>
  <div class="token-page" v-loading="loading">
    <header class="page-header">
      <div>
        <h1 class="page-title">
          <span class="title-pixel" aria-hidden="true">■</span>
          {{ t('tokenStats.title') }}
        </h1>
        <p class="page-desc">// {{ t('tokenStats.desc') }}</p>
      </div>
      <div class="filter-group" role="radiogroup">
        <button
          v-for="r in timeRangeKeys"
          :key="r.value"
          role="radio"
          :aria-checked="timeRange === r.value"
          class="filter-btn"
          :class="{ active: timeRange === r.value }"
          @click="timeRange = r.value"
        >
          {{ t(r.key) }}
        </button>
      </div>
    </header>

    <section class="summary-grid">
      <article class="summary-card">
        <div class="summary-pixel-bar red" aria-hidden="true"></div>
        <div class="summary-value">{{ formatTokens(summary.total_input_tokens) }}</div>
        <div class="summary-label">{{ t('tokenStats.inputTokens') }}</div>
      </article>
      <article class="summary-card">
        <div class="summary-pixel-bar green" aria-hidden="true"></div>
        <div class="summary-value">{{ formatTokens(summary.total_output_tokens) }}</div>
        <div class="summary-label">{{ t('tokenStats.outputTokens') }}</div>
      </article>
      <article class="summary-card">
        <div class="summary-pixel-bar black" aria-hidden="true"></div>
        <div class="summary-value">{{ formatTokens(summary.total_tokens) }}</div>
        <div class="summary-label">{{ t('tokenStats.totalTokens') }}</div>
      </article>
    </section>

    <section class="panel trend-panel">
      <div class="panel-header">
        <h2 class="panel-title"><span class="panel-pixel" aria-hidden="true">▸</span> {{ t('tokenStats.trendTitle') }}</h2>
      </div>
      <div class="chart-body" v-if="trend.length > 0"><TokenChart :data="trend" /></div>
      <div v-else class="empty-state" role="status"><span>{{ t('tokenStats.noTrend') }}</span></div>
    </section>

    <div class="rankings-grid">
      <section class="panel">
        <div class="panel-header">
          <h2 class="panel-title"><span class="panel-pixel" aria-hidden="true">▸</span> {{ t('tokenStats.rankInstance') }}</h2>
        </div>
        <div class="chart-body-sm" v-if="summary.by_instance.length > 0">
          <v-chart :option="instanceBarOption()" autoresize style="height: 100%; width: 100%" />
        </div>
        <div v-else class="empty-state-sm" role="status"><span>{{ t('tokenStats.noData') }}</span></div>
      </section>
      <section class="panel">
        <div class="panel-header">
          <h2 class="panel-title"><span class="panel-pixel" aria-hidden="true">▸</span> {{ t('tokenStats.rankAgent') }}</h2>
        </div>
        <div class="chart-body-sm" v-if="summary.by_agent.length > 0">
          <v-chart :option="agentBarOption()" autoresize style="height: 100%; width: 100%" />
        </div>
        <div v-else class="empty-state-sm" role="status"><span>{{ t('tokenStats.noData') }}</span></div>
      </section>
    </div>

    <section class="section detail-section">
      <div class="section-header">
        <h2 class="section-title"><span class="section-pixel" aria-hidden="true">▸</span> {{ t('tokenStats.detailTitle') }}</h2>
      </div>
      <div class="table-panel">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">{{ t('tokenStats.colInstance') }}</th>
              <th scope="col" class="right">{{ t('tokenStats.colTokens') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary.by_instance" :key="row.instance_id">
              <td class="cell-name">{{ row.instance_name }}</td>
              <td class="right cell-mono highlight">{{ formatTokens(row.total_tokens) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.token-page { }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-6); gap: var(--space-4); }
.page-title { font-size: 22px; display: flex; align-items: center; gap: var(--space-2); }
.title-pixel { color: var(--accent); font-size: 16px; }
.page-desc { font-size: 13px; color: var(--text-muted); margin-top: var(--space-1); font-family: var(--font-mono); }

.filter-group { display: flex; border: 2px solid var(--border-strong); flex-shrink: 0; }
.filter-btn { padding: var(--space-2) var(--space-3); border: none; border-right: 2px solid var(--border-strong); background: var(--bg-surface); color: var(--text-secondary); font-family: var(--font-pixel); font-size: 10px; cursor: pointer; transition: all var(--duration-fast) ease; }
.filter-btn:last-child { border-right: none; }
.filter-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.filter-btn:active { background: var(--bg-active); }
.filter-btn.active { color: white; background: var(--text-primary); }

.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-4); margin-bottom: var(--space-6); }
.summary-card { background: var(--bg-surface); border: 2px solid var(--border); padding: var(--space-5) var(--space-4); text-align: center; position: relative; overflow: hidden; transition: all var(--duration-fast) ease; }
.summary-card:hover { border-color: var(--border-strong); transform: translateY(-2px); box-shadow: 4px 4px 0 var(--border); }
.summary-pixel-bar { position: absolute; top: 0; left: 0; right: 0; height: 4px; }
.summary-pixel-bar.red { background: var(--accent); }
.summary-pixel-bar.green { background: var(--green); }
.summary-pixel-bar.black { background: var(--text-primary); }
.summary-value { font-family: var(--font-mono); font-size: 24px; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.summary-label { font-family: var(--font-pixel); font-size: 9px; color: var(--text-muted); margin-top: var(--space-2); letter-spacing: 1px; }

.panel { background: var(--bg-surface); border: 2px solid var(--border); overflow: hidden; }
.trend-panel { margin-bottom: var(--space-4); }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-4); border-bottom: 2px dashed var(--border); background: var(--bg-elevated); }
.panel-title { display: flex; align-items: center; gap: var(--space-2); font-size: 13px; letter-spacing: 0.3px; color: var(--text-secondary); }
.panel-pixel { color: var(--accent); }
.chart-body { height: 350px; padding: var(--space-3); }
.chart-body-sm { height: 300px; padding: var(--space-3); }
.empty-state, .empty-state-sm { display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 13px; }
.empty-state { height: 350px; }
.empty-state-sm { height: 300px; }

.rankings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: var(--space-4); }

.section { margin-bottom: var(--space-6); }
.detail-section { margin-top: var(--space-4); }
.section-header { display: flex; align-items: center; margin-bottom: var(--space-3); }
.section-title { display: flex; align-items: center; gap: var(--space-2); font-size: 15px; color: var(--text-primary); }
.section-pixel { color: var(--accent); }

.table-panel { background: var(--bg-surface); border: 2px solid var(--border); overflow: hidden; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead { background: var(--bg-elevated); }
.data-table th { padding: var(--space-3) var(--space-4); font-size: 11px; font-weight: 700; color: var(--text-muted); text-align: left; border-bottom: 2px solid var(--border); text-transform: uppercase; letter-spacing: 0.5px; }
.data-table th.right { text-align: right; }
.data-table tbody tr { border-bottom: 1px dashed var(--border); transition: background var(--duration-fast) ease; }
.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody tr:hover { background: var(--bg-hover); }
.data-table td { padding: var(--space-3) var(--space-4); font-size: 13px; color: var(--text-primary); }
.data-table td.right { text-align: right; }
.cell-name { font-weight: 600; }
.cell-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.highlight { color: var(--accent) !important; font-weight: 600; }

@media (max-width: 768px) { .page-header { flex-direction: column; } .page-title { font-size: 18px; } .rankings-grid { grid-template-columns: 1fr; } }
</style>
