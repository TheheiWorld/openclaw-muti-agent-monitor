<script setup lang="ts">
import { ref, watch } from 'vue'
import { getAgentDocs } from '../api'
import { useI18n } from '../i18n'

const props = defineProps<{
  visible: boolean
  agentId: string
  instanceId: string
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

const { t } = useI18n()
const loading = ref(false)
const files = ref<Record<string, string>>({})
const activeTab = ref('')

const TAB_ORDER = ['SOUL.md', 'AGENTS.md', 'IDENTITY.md', 'USER.md', 'TOOLS.md']

watch(() => props.visible, async (val) => {
  if (!val) return
  loading.value = true
  files.value = {}
  activeTab.value = ''
  try {
    const res = await getAgentDocs(props.agentId, props.instanceId)
    files.value = res.data.files || {}
    const firstAvailable = TAB_ORDER.find(name => files.value[name])
    activeTab.value = firstAvailable || ''
  } catch (e) {
    console.error('Failed to load agent docs', e)
  } finally {
    loading.value = false
  }
})

const handleOverlayClick = (e: MouseEvent) => {
  if (e.target === e.currentTarget) emit('close')
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="ws-overlay"
      @click="handleOverlayClick"
      @keydown="handleKeydown"
      tabindex="-1"
      ref="overlayRef"
    >
      <div class="ws-panel">
        <div class="pixel-corner tl" aria-hidden="true"></div>
        <div class="pixel-corner tr" aria-hidden="true"></div>

        <!-- Header -->
        <div class="ws-header">
          <h2 class="ws-title">
            <span class="title-pixel" aria-hidden="true">&#9632;</span>
            {{ t('agentDetail.workspaceTitle') }}
          </h2>
          <button class="ws-close" @click="emit('close')" :aria-label="t('agentDetail.workspaceClose')">
            &times;
          </button>
        </div>

        <!-- Tabs -->
        <div class="ws-tabs">
          <button
            v-for="name in TAB_ORDER"
            :key="name"
            class="ws-tab"
            :class="{ active: activeTab === name, disabled: !files[name] }"
            :disabled="!files[name]"
            @click="activeTab = name"
          >{{ name }}</button>
        </div>

        <!-- Content -->
        <div class="ws-body" v-loading="loading">
          <pre v-if="activeTab && files[activeTab]" class="ws-content">{{ files[activeTab] }}</pre>
          <div v-else-if="!loading" class="ws-empty">
            {{ t('agentDetail.workspaceEmpty') }}
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ws-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  padding: var(--space-6);
}

.ws-panel {
  position: relative;
  width: 100%;
  height: 100%;
  max-width: 1200px;
  max-height: 100%;
  background: var(--bg-surface);
  border: 2px solid var(--border-strong);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ws-panel .pixel-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  background: var(--accent);
}
.ws-panel .pixel-corner.tl { top: -2px; left: -2px; }
.ws-panel .pixel-corner.tr { top: -2px; right: -2px; }

.ws-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 2px dashed var(--border);
  background: var(--bg-elevated);
  flex-shrink: 0;
}

.ws-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 15px;
  color: var(--text-primary);
  margin: 0;
}
.title-pixel { color: var(--accent); font-size: 14px; }

.ws-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}
.ws-close:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-light);
}

.ws-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--border);
  background: var(--bg-elevated);
  flex-shrink: 0;
  overflow-x: auto;
}

.ws-tab {
  padding: var(--space-3) var(--space-4);
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-fast) ease;
  margin-bottom: -2px;
}
.ws-tab:hover:not(.disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
}
.ws-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  background: var(--bg-surface);
}
.ws-tab.disabled {
  color: var(--text-muted);
  opacity: 0.5;
  cursor: not-allowed;
}

.ws-body {
  flex: 1;
  overflow: auto;
  padding: var(--space-5);
  min-height: 0;
}

.ws-content {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.ws-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 14px;
}

@media (max-width: 768px) {
  .ws-overlay { padding: 0; }
  .ws-panel { max-width: 100%; border: none; }
  .ws-tab { padding: var(--space-2) var(--space-3); font-size: 11px; }
}
</style>
