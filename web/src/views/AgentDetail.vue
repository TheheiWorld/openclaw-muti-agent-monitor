<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { getAgent, getAgentSessions, deleteAgent } from '../api'
import { useI18n } from '../i18n'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const loading = ref(true)
const agent = ref<any>(null)
const sessions = ref<any[]>([])

const formatTokens = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

const formatTime = (iso: string | null) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

const fetchData = async () => {
  loading.value = true
  try {
    const agentId = route.params.id as string
    const instanceId = route.query.instance_id as string
    const [agentRes, sessionsRes] = await Promise.all([
      getAgent(agentId, instanceId),
      getAgentSessions(agentId, { instance_id: instanceId }),
    ])
    agent.value = agentRes.data
    sessions.value = sessionsRes.data.items
  } catch (e) {
    console.error('Failed to load agent detail', e)
  } finally {
    loading.value = false
  }
}

const handleDelete = async () => {
  if (!agent.value) return
  const name = agent.value.name || agent.value.agent_id
  const msg = t('agentDetail.deleteConfirm').replace('{name}', name)
  try {
    await ElMessageBox.confirm(msg, { confirmButtonText: t('auth.confirm'), cancelButtonText: t('auth.cancel'), type: 'warning' })
    await deleteAgent(agent.value.agent_id, agent.value.instance_id)
    ElMessage.success(t('agentDetail.deleteSuccess'))
    router.back()
  } catch (err: any) {
    if (err === 'cancel') return
    ElMessage.error(err?.response?.data?.detail || 'Delete failed')
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="detail-page" v-loading="loading">
    <div class="top-bar">
      <button class="back-btn" @click="router.back()">
        <span aria-hidden="true">&larr;</span>
        <span>{{ t('detail.back') }}</span>
      </button>
      <button
        v-if="agent && agent.status === 'offline'"
        class="delete-btn"
        @click="handleDelete"
      >{{ t('agentDetail.delete') }}</button>
    </div>

    <template v-if="agent">
      <header class="page-header">
        <div class="title-row">
          <h1 class="page-title">
            <span class="title-pixel" aria-hidden="true">■</span>
            <span v-if="agent.identity_emoji" class="agent-emoji">{{ agent.identity_emoji }}</span>
            {{ agent.name || agent.agent_id }}
          </h1>
          <StatusBadge :status="agent.status" />
        </div>
        <p class="page-desc">// {{ agent.instance_name }} · {{ agent.agent_id }}</p>
      </header>

      <section class="info-panel">
        <div class="info-panel-header">
          <span class="info-pixel" aria-hidden="true">&#9656;</span>
          {{ t('agentDetail.infoTitle') }}
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldId') }}</span>
            <span class="info-value mono">{{ agent.agent_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldName') }}</span>
            <span class="info-value">{{ agent.name || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldInstance') }}</span>
            <span class="info-value">{{ agent.instance_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldStatus') }}</span>
            <span class="info-value"><StatusBadge :status="agent.status" /></span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldSessions') }}</span>
            <span class="info-value mono">{{ agent.session_count }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldTokens') }}</span>
            <span class="info-value mono highlight">{{ formatTokens(agent.total_tokens) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldCost') }}</span>
            <span class="info-value mono">${{ agent.estimated_cost_usd }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('agentDetail.fieldUpdated') }}</span>
            <span class="info-value mono">{{ formatTime(agent.updated_at) }}</span>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="section-pixel" aria-hidden="true">&#9656;</span>
            {{ t('agentDetail.sessionTitle') }}
          </h2>
          <span class="section-count">{{ sessions.length }}</span>
        </div>
        <div class="table-panel">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">{{ t('detail.sessionColId') }}</th>
                <th scope="col">{{ t('detail.sessionColChannel') }}</th>
                <th scope="col">{{ t('detail.sessionColUser') }}</th>
                <th scope="col">{{ t('detail.sessionColStatus') }}</th>
                <th scope="col" class="right">{{ t('detail.sessionColInput') }}</th>
                <th scope="col" class="right">{{ t('detail.sessionColOutput') }}</th>
                <th scope="col" class="right">{{ t('detail.sessionColTotal') }}</th>
                <th scope="col">{{ t('detail.sessionColModel') }}</th>
                <th scope="col">{{ t('detail.sessionColUpdated') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in sessions" :key="row.session_id">
                <td class="cell-mono truncate" :title="row.session_id">{{ row.session_id }}</td>
                <td class="cell-mono">{{ row.channel || '-' }}</td>
                <td class="truncate" :title="row.display_name">{{ row.display_name || '-' }}</td>
                <td><StatusBadge :status="row.status" /></td>
                <td class="right cell-mono">{{ formatTokens(row.input_tokens) }}</td>
                <td class="right cell-mono">{{ formatTokens(row.output_tokens) }}</td>
                <td class="right cell-mono highlight">{{ formatTokens(row.total_tokens) }}</td>
                <td class="cell-mono truncate" :title="row.model">{{ row.model || '-' }}</td>
                <td class="cell-time">{{ formatTime(row.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="sessions.length === 0" class="empty-state" role="status">
            <span>{{ t('agentDetail.noSessions') }}</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.detail-page { }

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
}

.back-btn {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border: 2px solid var(--border);
  background: var(--bg-surface); color: var(--text-secondary);
  font-family: var(--font-body); font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all var(--duration-fast) ease;
}
.back-btn:hover { color: var(--text-primary); border-color: var(--border-strong); background: var(--bg-hover); }

.delete-btn {
  padding: var(--space-2) var(--space-3);
  border: 2px solid var(--red);
  background: transparent;
  color: var(--red);
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}
.delete-btn:hover { background: var(--red); color: white; }

.page-header { margin-bottom: var(--space-6); }
.title-row { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
.page-title { font-size: 22px; display: flex; align-items: center; gap: var(--space-2); }
.title-pixel { color: var(--accent); font-size: 16px; }
.agent-emoji { font-size: 20px; }
.page-desc { font-family: var(--font-mono); font-size: 13px; color: var(--text-muted); margin-top: var(--space-1); }

.info-panel { background: var(--bg-surface); border: 2px solid var(--border); margin-bottom: var(--space-6); }
.info-panel-header { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4); background: var(--bg-elevated); border-bottom: 2px dashed var(--border); font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.info-pixel { color: var(--accent); }

.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
.info-item { display: flex; flex-direction: column; gap: 2px; padding: var(--space-4); border-right: 1px dashed var(--border); border-bottom: 1px dashed var(--border); }
.info-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); }
.info-value { font-size: 14px; color: var(--text-primary); font-weight: 500; }
.info-value.mono { font-family: var(--font-mono); font-size: 13px; color: var(--text-secondary); }
.info-value.highlight { color: var(--accent) !important; font-weight: 600; }

.section { margin-bottom: var(--space-6); }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-3); }
.section-title { display: flex; align-items: center; gap: var(--space-2); font-size: 15px; color: var(--text-primary); }
.section-pixel { color: var(--accent); }
.section-count { font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: var(--text-muted); padding: var(--space-1) var(--space-2); border: 2px solid var(--border); background: var(--bg-surface); }

.table-panel { background: var(--bg-surface); border: 2px solid var(--border); overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead { background: var(--bg-elevated); }
.data-table th { padding: var(--space-3) var(--space-4); font-size: 11px; font-weight: 700; color: var(--text-muted); text-align: left; border-bottom: 2px solid var(--border); white-space: nowrap; text-transform: uppercase; letter-spacing: 0.5px; }
.data-table th.right { text-align: right; }
.data-table tbody tr { border-bottom: 1px dashed var(--border); transition: background var(--duration-fast) ease; }
.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody tr:hover { background: var(--bg-hover); }
.data-table td { padding: var(--space-3) var(--space-4); font-size: 13px; color: var(--text-primary); vertical-align: middle; }
.data-table td.right { text-align: right; }
.cell-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.cell-time { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); white-space: nowrap; }
.truncate { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.highlight { color: var(--accent) !important; font-weight: 600; }

.empty-state { display: flex; align-items: center; justify-content: center; padding: var(--space-8) var(--space-4); color: var(--text-muted); font-size: 13px; }

@media (max-width: 576px) { .page-title { font-size: 18px; } }
</style>
