<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboard } from '../api'
import { useI18n } from '../i18n'
import StatusBadge from '../components/StatusBadge.vue'
import TokenChart from '../components/TokenChart.vue'

const router = useRouter()
const { t } = useI18n()
const loading = ref(true)
const dashboard = ref<any>({
  instances: { total: 0, online: 0, offline: 0, unhealthy: 0 },
  agents: { total: 0 },
  tokens: { total_input: 0, total_output: 0, total: 0, total_cost_usd: 0, today_total: 0 },
  alerts: [],
  trend_24h: [],
})

let timer: number | undefined

const fetchData = async () => {
  try {
    const res = await getDashboard()
    dashboard.value = res.data
  } catch (e) {
    console.error('Failed to load dashboard', e)
  } finally {
    loading.value = false
  }
}

const formatTokens = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

onMounted(() => {
  fetchData()
  timer = window.setInterval(fetchData, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const statCards = [
  { key: 'instances', pixel: '▦', labelKey: 'dashboard.statInstances' },
  { key: 'agents', pixel: '▣', labelKey: 'dashboard.statAgents' },
  { key: 'tokens', pixel: '◈', labelKey: 'dashboard.statTokens' },
]

const getStatValue = (key: string) => {
  switch (key) {
    case 'instances': return `${dashboard.value.instances.online} / ${dashboard.value.instances.total}`
    case 'agents': return dashboard.value.agents.total
    case 'tokens': return formatTokens(dashboard.value.tokens.today_total)
    default: return '-'
  }
}
</script>

<template>
  <div class="dashboard" v-loading="loading">
    <header class="page-header">
      <div>
        <h1 class="page-title">
          <span class="title-pixel" aria-hidden="true">■</span>
          {{ t('dashboard.title') }}
        </h1>
        <p class="page-desc">// {{ t('dashboard.desc') }}</p>
      </div>
      <div class="header-live" role="status" aria-live="polite">
        <span class="live-pixel" aria-hidden="true"></span>
        <span>{{ t('dashboard.live') }}</span>
      </div>
    </header>

    <section class="stat-grid" aria-label="关键指标">
      <article
        v-for="card in statCards"
        :key="card.key"
        class="stat-card"
      >
        <div class="stat-card-inner">
          <span class="stat-pixel" aria-hidden="true">{{ card.pixel }}</span>
          <div class="stat-content">
            <div class="stat-value">{{ getStatValue(card.key) }}</div>
            <div class="stat-label">{{ t(card.labelKey) }}</div>
          </div>
        </div>
        <div class="stat-corner" aria-hidden="true"></div>
      </article>
    </section>

    <div class="content-grid">
      <section class="panel" aria-label="Token 用量趋势">
        <div class="panel-header">
          <h2 class="panel-title">
            <span class="panel-pixel" aria-hidden="true">▸</span>
            {{ t('dashboard.trendTitle') }}
          </h2>
        </div>
        <div class="chart-body" v-if="dashboard.trend_24h.length > 0">
          <TokenChart :data="dashboard.trend_24h" />
        </div>
        <div v-else class="empty-state" role="status">
          <span class="empty-pixel" aria-hidden="true">□</span>
          <span>{{ t('dashboard.noData') }}</span>
        </div>
      </section>

      <section class="panel alerts-panel" aria-label="异常告警">
        <div class="panel-header">
          <h2 class="panel-title">
            <span class="panel-pixel" aria-hidden="true">▸</span>
            {{ t('dashboard.alertsTitle') }}
          </h2>
          <span v-if="dashboard.alerts.length > 0" class="alert-count" role="status">{{ dashboard.alerts.length }}</span>
        </div>
        <div class="alerts-body">
          <div v-if="dashboard.alerts.length === 0" class="all-clear" role="status">
            <div class="all-clear-icon" aria-hidden="true">✓</div>
            <span class="all-clear-text">{{ t('dashboard.allClear') }}</span>
          </div>
          <ul v-else class="alert-list" role="list">
            <li
              v-for="alert in dashboard.alerts"
              :key="alert.instance_id"
              class="alert-item"
              tabindex="0"
              @click="router.push(`/instances/${alert.instance_id}`)"
              @keydown.enter="router.push(`/instances/${alert.instance_id}`)"
            >
              <div class="alert-info">
                <div class="alert-name">{{ alert.name }}</div>
                <div class="alert-host">{{ alert.host }}</div>
              </div>
              <StatusBadge :status="alert.status" />
            </li>
          </ul>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1200px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-8);
  gap: var(--space-4);
}

.page-title {
  font-size: 22px;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.title-pixel { color: var(--accent); font-size: 16px; }

.page-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: var(--space-1);
  font-family: var(--font-mono);
}

.header-live {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-pixel);
  font-size: 11px;
  color: var(--green);
  padding: var(--space-1) var(--space-3);
  border: 2px solid var(--green);
  background: var(--green-light);
  flex-shrink: 0;
}

.live-pixel {
  width: 8px;
  height: 8px;
  background: var(--green);
  animation: pixel-blink 1s step-end infinite;
}

@keyframes pixel-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  position: relative;
  background: var(--bg-surface);
  border: 2px solid var(--border);
  padding: var(--space-5);
  transition: all var(--duration-fast) ease;
  overflow: hidden;
}

.stat-card:hover {
  border-color: var(--border-strong);
  transform: translateY(-2px);
  box-shadow: 4px 4px 0 var(--border);
}

.stat-card-inner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.stat-pixel { font-size: 28px; color: var(--accent); flex-shrink: 0; line-height: 1; }

.stat-value {
  font-family: var(--font-mono);
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.stat-corner {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 12px;
  height: 12px;
  background: repeating-linear-gradient(45deg, var(--border) 0px, var(--border) 2px, transparent 2px, transparent 4px);
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: var(--space-4);
}

.panel {
  background: var(--bg-surface);
  border: 2px solid var(--border);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 2px dashed var(--border);
  background: var(--bg-elevated);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  letter-spacing: 0.3px;
  color: var(--text-secondary);
}

.panel-pixel { color: var(--accent); }

.alert-count {
  min-width: 24px;
  height: 20px;
  padding: 0 var(--space-2);
  background: var(--accent);
  color: white;
  font-family: var(--font-pixel);
  font-size: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.chart-body { height: 320px; padding: var(--space-3); }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: 320px;
  color: var(--text-muted);
  font-size: 13px;
}

.empty-pixel { font-size: 32px; opacity: 0.3; }

.alerts-body {
  padding: var(--space-3);
  min-height: 320px;
  display: flex;
  flex-direction: column;
}

.all-clear {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.all-clear-icon { font-family: var(--font-pixel); font-size: 32px; color: var(--green); }
.all-clear-text { font-size: 13px; color: var(--green); font-family: var(--font-mono); }

.alert-list { display: flex; flex-direction: column; gap: 2px; list-style: none; }

.alert-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  transition: all var(--duration-fast) ease;
  border: 2px solid transparent;
}

.alert-item:hover, .alert-item:focus-visible {
  background: var(--bg-hover);
  border-color: var(--border);
}

.alert-item:active { background: var(--bg-active); }

.alert-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.alert-host { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-top: 1px; }

@media (max-width: 992px) { .content-grid { grid-template-columns: 1fr; } }
@media (max-width: 576px) { .page-header { flex-direction: column; } .page-title { font-size: 18px; } }
</style>
