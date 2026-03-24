<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { getInstances, deleteInstance } from '../api'
import { useI18n } from '../i18n'
import StatusBadge from '../components/StatusBadge.vue'

const router = useRouter()
const { t } = useI18n()
const loading = ref(true)
const instances = ref<any[]>([])
const statusFilter = ref('')

const filterKeys = [
  { value: '', key: 'instances.filterAll' },
  { value: 'online', key: 'instances.filterOnline' },
  { value: 'offline', key: 'instances.filterOffline' },
  { value: 'unhealthy', key: 'instances.filterUnhealthy' },
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
    const params: any = {}
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getInstances(params)
    instances.value = res.data.items
  } catch (e) {
    console.error('Failed to load instances', e)
  } finally {
    loading.value = false
  }
}

const handleRowClick = (id: string) => { router.push(`/instances/${id}`) }
const handleRowKeydown = (e: KeyboardEvent, id: string) => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleRowClick(id) }
}

const handleDelete = async (e: Event, row: any) => {
  e.stopPropagation()
  const msg = t('instances.deleteConfirm').replace('{name}', row.name)
  try {
    await ElMessageBox.confirm(msg, { confirmButtonText: t('auth.confirm'), cancelButtonText: t('auth.cancel'), type: 'warning' })
    await deleteInstance(row.instance_id)
    ElMessage.success(t('instances.deleteSuccess'))
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
  <div class="instances-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">
          <span class="title-pixel" aria-hidden="true">■</span>
          {{ t('instances.title') }}
        </h1>
        <p class="page-desc">// {{ t('instances.desc') }}</p>
      </div>
      <div class="filter-group" role="radiogroup" aria-label="状态筛选">
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
            <th scope="col">{{ t('instances.colName') }}</th>
            <th scope="col">{{ t('instances.colHostname') }}</th>
            <th scope="col">{{ t('instances.colHost') }}</th>
            <th scope="col">{{ t('instances.colStatus') }}</th>
            <th scope="col">{{ t('instances.colVersion') }}</th>
            <th scope="col" class="center">{{ t('instances.colAgentCount') }}</th>
            <th scope="col" class="right">{{ t('instances.colTokens') }}</th>
            <th scope="col">{{ t('instances.colHeartbeat') }}</th>
            <th scope="col" class="center">{{ t('instances.colAction') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in instances"
            :key="row.instance_id"
            tabindex="0"
            role="link"
            @click="handleRowClick(row.instance_id)"
            @keydown="handleRowKeydown($event, row.instance_id)"
          >
            <td class="cell-name">{{ row.name }}</td>
            <td class="cell-mono">{{ row.hostname || '-' }}</td>
            <td class="cell-mono">{{ row.host }}:{{ row.port }}</td>
            <td><StatusBadge :status="row.status" /></td>
            <td class="cell-mono">{{ row.version }}</td>
            <td class="center cell-mono">{{ row.agent_count }}</td>
            <td class="right cell-mono">{{ formatTokens(row.total_tokens) }}</td>
            <td class="cell-time">{{ formatTime(row.last_heartbeat) }}</td>
            <td class="center">
              <button
                v-if="row.status === 'offline'"
                class="delete-btn"
                @click.stop="handleDelete($event, row)"
              >{{ t('instances.delete') }}</button>
              <span v-else class="cell-mono">-</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && instances.length === 0" class="empty-state" role="status">
        <span class="empty-pixel" aria-hidden="true">□</span>
        <span>{{ t('instances.empty') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.instances-page { max-width: 1200px; }

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
  cursor: pointer;
  transition: all var(--duration-fast) ease;
  border-bottom: 1px dashed var(--border);
}

.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody tr:hover, .data-table tbody tr:focus-visible { background: var(--bg-hover); }
.data-table tbody tr:hover .cell-name { color: var(--accent); }
.data-table tbody tr:active { background: var(--bg-active); }

.data-table td { padding: var(--space-3) var(--space-4); font-size: 13px; color: var(--text-primary); vertical-align: middle; }
.data-table td.center { text-align: center; }
.data-table td.right { text-align: right; }

.cell-name { font-weight: 600; transition: color var(--duration-fast) ease; }
.cell-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.cell-time { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

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
