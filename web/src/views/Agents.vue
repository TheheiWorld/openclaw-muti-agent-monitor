<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { getAgents, deleteAgent } from '../api'
import { useI18n } from '../i18n'
import StatusBadge from '../components/StatusBadge.vue'

const { t } = useI18n()
const loading = ref(true)
const agents = ref<any[]>([])
const statusFilter = ref('')

const filterKeys = [
  { value: '', key: 'agents.filterAll' },
  { value: 'active', key: 'agents.filterActive' },
  { value: 'offline', key: 'agents.filterOffline' },
]

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
    const res = await getAgents()
    let items = res.data.items
    if (statusFilter.value) {
      items = items.filter((a: any) => a.status === statusFilter.value)
    }
    agents.value = items
  } catch (e) {
    console.error('Failed to load agents', e)
  } finally {
    loading.value = false
  }
}

const handleDelete = async (row: any) => {
  const name = row.name || row.agent_id
  const msg = t('agents.deleteConfirm').replace('{name}', name)
  try {
    await ElMessageBox.confirm(msg, { confirmButtonText: t('auth.confirm'), cancelButtonText: t('auth.cancel'), type: 'warning' })
    await deleteAgent(row.agent_id, row.instance_id)
    ElMessage.success(t('agents.deleteSuccess'))
    fetchData()
  } catch (err: any) {
    if (err === 'cancel') return
    ElMessage.error(err?.response?.data?.detail || 'Delete failed')
  }
}

onMounted(fetchData)
watch(statusFilter, fetchData)
</script>

<template>
  <div class="agents-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">
          <span class="title-pixel" aria-hidden="true">■</span>
          {{ t('agents.title') }}
        </h1>
        <p class="page-desc">// {{ t('agents.desc') }}</p>
      </div>
      <div class="filter-group" role="radiogroup">
        <button
          v-for="f in filterKeys"
          :key="f.value"
          role="radio"
          :aria-checked="statusFilter === f.value"
          class="filter-btn"
          :class="{ active: statusFilter === f.value }"
          @click="statusFilter = f.value"
        >
          {{ t(f.key) }}
        </button>
      </div>
    </header>

    <div class="table-panel" v-loading="loading">
      <table class="data-table" role="table">
        <thead>
          <tr>
            <th scope="col">{{ t('agents.colName') }}</th>
            <th scope="col">{{ t('agents.colId') }}</th>
            <th scope="col">{{ t('agents.colInstance') }}</th>
            <th scope="col">{{ t('agents.colStatus') }}</th>
            <th scope="col" class="center">{{ t('agents.colSessions') }}</th>
            <th scope="col" class="right">{{ t('agents.colTokens') }}</th>
            <th scope="col">{{ t('agents.colUpdated') }}</th>
            <th scope="col" class="center">{{ t('agents.colAction') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in agents" :key="row.instance_id + ':' + row.agent_id">
            <td class="cell-name">
              <span v-if="row.identity_emoji" aria-hidden="true">{{ row.identity_emoji }} </span>
              {{ row.name || row.agent_id }}
            </td>
            <td class="cell-mono">{{ row.agent_id }}</td>
            <td class="cell-mono">{{ row.instance_name }}</td>
            <td><StatusBadge :status="row.status" /></td>
            <td class="center cell-mono">{{ row.session_count }}</td>
            <td class="right cell-mono">{{ formatTokens(row.total_tokens) }}</td>
            <td class="cell-time">{{ formatTime(row.updated_at) }}</td>
            <td class="center">
              <button
                v-if="row.status === 'offline'"
                class="delete-btn"
                @click.stop="handleDelete(row)"
              >{{ t('agents.delete') }}</button>
              <span v-else class="cell-mono">-</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && agents.length === 0" class="empty-state" role="status">
        <span class="empty-pixel" aria-hidden="true">□</span>
        <span>{{ t('agents.empty') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agents-page { }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-6);
  gap: var(--space-4);
}

.page-title {
  font-size: 22px;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.title-pixel { color: var(--accent); font-size: 16px; }

.page-desc { font-size: 13px; color: var(--text-muted); margin-top: var(--space-1); font-family: var(--font-mono); }

.filter-group {
  display: flex;
  border: 2px solid var(--border-strong);
  flex-shrink: 0;
}

.filter-btn {
  padding: var(--space-2) var(--space-3);
  border: none;
  border-right: 2px solid var(--border-strong);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.filter-btn:last-child { border-right: none; }
.filter-btn:hover { color: var(--text-primary); background: var(--bg-hover); }
.filter-btn:active { background: var(--bg-active); }
.filter-btn.active { color: white; background: var(--text-primary); }

.table-panel { background: var(--bg-surface); border: 2px solid var(--border); overflow-x: auto; }

.data-table { width: 100%; border-collapse: collapse; }

.data-table thead { background: var(--bg-elevated); }

.data-table th {
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  text-align: left;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
  text-transform: uppercase;
}

.data-table th.center { text-align: center; }
.data-table th.right { text-align: right; }

.data-table tbody tr {
  transition: all var(--duration-fast) ease;
  border-bottom: 1px dashed var(--border);
}

.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody tr:hover { background: var(--bg-hover); }

.data-table td { padding: var(--space-3) var(--space-4); font-size: 13px; color: var(--text-primary); vertical-align: middle; }
.data-table td.center { text-align: center; }
.data-table td.right { text-align: right; }

.cell-name { font-weight: 600; }
.cell-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.cell-time { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); white-space: nowrap; }

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

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-2); padding: var(--space-16) var(--space-4); color: var(--text-muted); font-size: 13px; }
.empty-pixel { font-size: 32px; opacity: 0.3; }

@media (max-width: 768px) { .page-header { flex-direction: column; } .page-title { font-size: 18px; } .filter-group { width: 100%; overflow-x: auto; } }
</style>
