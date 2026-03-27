<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { getInstance, deleteAgent } from '../api'
import { useI18n } from '../i18n'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const loading = ref(true)
const instance = ref<any>(null)

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
    const id = route.params.id as string
    const res = await getInstance(id)
    instance.value = res.data
  } catch (e) {
    console.error('Failed to load instance', e)
  } finally {
    loading.value = false
  }
}

const handleDeleteAgent = async (row: any) => {
  const name = row.name || row.agent_id
  const msg = t('detail.agentDeleteConfirm').replace('{name}', name)
  try {
    await ElMessageBox.confirm(msg, { confirmButtonText: t('auth.confirm'), cancelButtonText: t('auth.cancel'), type: 'warning' })
    await deleteAgent(row.agent_id, instance.value.instance_id)
    ElMessage.success(t('detail.agentDeleteSuccess'))
    fetchData()
  } catch (err: any) {
    if (err === 'cancel') return
    ElMessage.error(err?.response?.data?.detail || 'Delete failed')
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="detail-page" v-loading="loading">
    <button class="back-btn" @click="router.back()">
      <span aria-hidden="true">←</span>
      <span>{{ t('detail.back') }}</span>
    </button>

    <template v-if="instance">
      <header class="page-header">
        <div class="title-row">
          <h1 class="page-title">
            <span class="title-pixel" aria-hidden="true">■</span>
            {{ instance.name || t('detail.defaultTitle') }}
          </h1>
          <StatusBadge :status="instance.status" />
        </div>
        <p class="page-desc">// {{ instance.host }}:{{ instance.port }}</p>
      </header>

      <section class="info-panel" aria-label="基本信息">
        <div class="info-panel-header">
          <span class="info-pixel" aria-hidden="true">▸</span>
          {{ t('detail.infoTitle') }}
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">{{ t('detail.fieldId') }}</span>
            <span class="info-value mono">{{ instance.instance_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('detail.fieldName') }}</span>
            <span class="info-value">{{ instance.name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('detail.fieldHostname') }}</span>
            <span class="info-value mono">{{ instance.hostname || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('detail.fieldVersion') }}</span>
            <span class="info-value mono">{{ instance.version || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('detail.fieldHost') }}</span>
            <span class="info-value mono">{{ instance.host }}:{{ instance.port }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('detail.fieldCreated') }}</span>
            <span class="info-value mono">{{ formatTime(instance.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('detail.fieldHeartbeat') }}</span>
            <span class="info-value mono">{{ formatTime(instance.last_heartbeat) }}</span>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="section-pixel" aria-hidden="true">▸</span>
            {{ t('detail.agentTitle') }}
          </h2>
          <span class="section-count">{{ instance.agents?.length || 0 }}</span>
        </div>
        <div class="table-panel">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">{{ t('detail.agentColName') }}</th>
                <th scope="col">{{ t('detail.agentColId') }}</th>
                <th scope="col">{{ t('detail.agentColStatus') }}</th>
                <th scope="col" class="center">{{ t('detail.agentColSessions') }}</th>
                <th scope="col" class="right">{{ t('detail.agentColTokens') }}</th>
                <th scope="col">{{ t('detail.agentColUpdated') }}</th>
                <th scope="col" class="center">{{ t('detail.agentColAction') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in instance.agents" :key="row.agent_id">
                <td class="cell-name">
                  <span v-if="row.identity_emoji" aria-hidden="true">{{ row.identity_emoji }} </span>
                  {{ row.name || row.agent_id }}
                </td>
                <td class="cell-mono">{{ row.agent_id }}</td>
                <td><StatusBadge :status="row.status" /></td>
                <td class="center cell-mono">{{ row.session_count }}</td>
                <td class="right cell-mono">{{ formatTokens(row.total_tokens) }}</td>
                <td class="cell-time">{{ formatTime(row.updated_at) }}</td>
                <td class="center">
                  <button
                    v-if="row.status === 'offline'"
                    class="delete-btn"
                    @click.stop="handleDeleteAgent(row)"
                  >{{ t('detail.agentDelete') }}</button>
                  <span v-else class="cell-mono">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.detail-page { }

.back-btn {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border: 2px solid var(--border);
  background: var(--bg-surface); color: var(--text-secondary);
  font-family: var(--font-body); font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all var(--duration-fast) ease; margin-bottom: var(--space-5);
}
.back-btn:hover { color: var(--text-primary); border-color: var(--border-strong); background: var(--bg-hover); }
.back-btn:active { background: var(--bg-active); }

.page-header { margin-bottom: var(--space-6); }
.title-row { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
.page-title { font-size: 22px; display: flex; align-items: center; gap: var(--space-2); }
.title-pixel { color: var(--accent); font-size: 16px; }
.page-desc { font-family: var(--font-mono); font-size: 13px; color: var(--text-muted); margin-top: var(--space-1); }

.info-panel { background: var(--bg-surface); border: 2px solid var(--border); margin-bottom: var(--space-6); }
.info-panel-header { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4); background: var(--bg-elevated); border-bottom: 2px dashed var(--border); font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.info-pixel { color: var(--accent); }

.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
.info-item { display: flex; flex-direction: column; gap: 2px; padding: var(--space-4); border-right: 1px dashed var(--border); border-bottom: 1px dashed var(--border); }
.info-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); }
.info-value { font-size: 14px; color: var(--text-primary); font-weight: 500; }
.info-value.mono { font-family: var(--font-mono); font-size: 13px; color: var(--text-secondary); }

.section { margin-bottom: var(--space-6); }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-3); }
.section-title { display: flex; align-items: center; gap: var(--space-2); font-size: 15px; color: var(--text-primary); }
.section-pixel { color: var(--accent); }
.section-count { font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: var(--text-muted); padding: var(--space-1) var(--space-2); border: 2px solid var(--border); background: var(--bg-surface); }

.table-panel { background: var(--bg-surface); border: 2px solid var(--border); overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead { background: var(--bg-elevated); }
.data-table th { padding: var(--space-3) var(--space-4); font-size: 11px; font-weight: 700; color: var(--text-muted); text-align: left; border-bottom: 2px solid var(--border); white-space: nowrap; text-transform: uppercase; letter-spacing: 0.5px; }
.data-table th.center { text-align: center; }
.data-table th.right { text-align: right; }
.data-table tbody tr { border-bottom: 1px dashed var(--border); transition: background var(--duration-fast) ease; }
.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody tr:hover { background: var(--bg-hover); }
.data-table td { padding: var(--space-3) var(--space-4); font-size: 13px; color: var(--text-primary); vertical-align: middle; }
.data-table td.center { text-align: center; }
.data-table td.right { text-align: right; }
.cell-name { font-weight: 600; }
.cell-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.cell-time { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); white-space: nowrap; }
.truncate { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (min-width: 1600px) { .truncate { max-width: 360px; } }
.highlight { color: var(--accent) !important; font-weight: 600; }

.delete-btn {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--red);
  background: transparent;
  color: var(--red);
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}
.delete-btn:hover { background: var(--red); color: white; }

@media (max-width: 576px) { .page-title { font-size: 18px; } }
</style>
