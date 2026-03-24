<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getRanks } from '../api'
import { useI18n } from '../i18n'

const { t } = useI18n()
const loading = ref(true)
const allAgents = ref<any[]>([])
const totalAgents = ref(0)
const hoveredAgent = ref<any>(null)
const tooltipPos = ref({ x: 0, y: 0 })

// 调色板 — 像素风配色
const palette = [
  '#D71921', '#2F54EB', '#1B873F', '#FA8C16', '#722ED1',
  '#13C2C2', '#EB2F96', '#D4A017', '#597EF7', '#52C41A',
  '#C27803', '#08979C', '#531DAB', '#A8111A', '#1D39C4',
  '#389E0D', '#D46B08', '#C41D7F', '#8B6914', '#595959',
]

const getColor = (idx: number) => palette[idx % palette.length]

// 像素点背景 SVG pattern（内联）
const pixelBg = (color: string) => {
  const encoded = encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="6" height="6"><rect width="5" height="5" fill="${color}" opacity="0.25"/></svg>`
  )
  return `url("data:image/svg+xml,${encoded}")`
}

// 根据 token 数量计算圆圈尺寸（最小60，最大220）
const bubbles = computed(() => {
  if (allAgents.value.length === 0) return []
  const tokens = allAgents.value.map(a => a.total_tokens || 1)
  const maxT = Math.max(...tokens)
  const minT = Math.min(...tokens)
  const range = maxT - minT || 1

  return allAgents.value.map((agent, idx) => {
    const ratio = (agent.total_tokens - minT) / range
    // 用 sqrt 让面积与 token 成正比
    const size = 60 + Math.sqrt(ratio) * 160
    const color = getColor(idx)
    return { ...agent, size, color, idx }
  })
})

const formatTokens = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

const onBubbleEnter = (e: MouseEvent, agent: any) => {
  hoveredAgent.value = agent
  updateTooltipPos(e)
}
const onBubbleMove = (e: MouseEvent) => {
  updateTooltipPos(e)
}
const onBubbleLeave = () => {
  hoveredAgent.value = null
}
const updateTooltipPos = (e: MouseEvent) => {
  tooltipPos.value = { x: e.clientX + 16, y: e.clientY + 16 }
}

onMounted(async () => {
  try {
    const res = await getRanks()
    // 展开所有 tier 中的 agents 到一个扁平列表
    const agents: any[] = []
    for (const tier of res.data.tiers) {
      for (const a of tier.agents) {
        agents.push({ ...a, rank_name: tier.rank_name, rank_emoji: tier.rank_emoji })
      }
    }
    allAgents.value = agents
    totalAgents.value = res.data.total_agents
  } catch (e) {
    console.error('Failed to load ranks', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="ranks-page" v-loading="loading">
    <header class="page-header">
      <div>
        <h1 class="page-title">
          <span class="title-pixel" aria-hidden="true">■</span>
          {{ t('ranks.title') }}
        </h1>
        <p class="page-desc">// {{ t('ranks.desc') }}</p>
      </div>
      <div class="total-badge">
        <span class="total-label">{{ t('ranks.totalAgents') }}</span>
        <span class="total-value">{{ totalAgents }}</span>
      </div>
    </header>

    <!-- 鸟瞰气泡图 -->
    <div class="birdseye">
      <div
        v-for="b in bubbles"
        :key="b.instance_id + ':' + b.agent_id"
        class="bubble"
        :style="{
          width: b.size + 'px',
          height: b.size + 'px',
          borderColor: b.color,
          backgroundImage: pixelBg(b.color),
          backgroundColor: b.color + '0A',
        }"
        @mouseenter="onBubbleEnter($event, b)"
        @mousemove="onBubbleMove"
        @mouseleave="onBubbleLeave"
      >
        <span class="bubble-name" :style="{ fontSize: Math.max(10, b.size / 8) + 'px', color: b.color }">
          {{ b.agent_name }}
        </span>
        <span class="bubble-tokens" :style="{ fontSize: Math.max(9, b.size / 10) + 'px' }">
          {{ formatTokens(b.total_tokens) }}
        </span>
      </div>
    </div>

    <!-- 悬浮详情卡 -->
    <Teleport to="body">
      <Transition name="tip">
        <div
          v-if="hoveredAgent"
          class="tooltip-card"
          :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
        >
          <div class="tip-header" :style="{ borderColor: hoveredAgent.color }">
            <span class="tip-rank">{{ hoveredAgent.rank_emoji }} {{ hoveredAgent.rank_name }}</span>
            <span class="tip-pos">#{{ hoveredAgent.position }}</span>
          </div>
          <div class="tip-name">{{ hoveredAgent.agent_name }}</div>
          <div class="tip-instance">{{ hoveredAgent.instance_name }}</div>
          <div class="tip-grid">
            <div class="tip-stat">
              <span class="tip-label">Tokens</span>
              <span class="tip-value" :style="{ color: hoveredAgent.color }">{{ formatTokens(hoveredAgent.total_tokens) }}</span>
            </div>
            <div class="tip-stat">
              <span class="tip-label">{{ t('ranks.sessions') }}</span>
              <span class="tip-value">{{ hoveredAgent.session_count }}</span>
            </div>
            <div class="tip-stat">
              <span class="tip-label">Cost</span>
              <span class="tip-value">${{ hoveredAgent.estimated_cost_usd }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <div v-if="!loading && allAgents.length === 0" class="empty-state" role="status">
      <span class="empty-pixel" aria-hidden="true">□</span>
      <span>{{ t('ranks.empty') }}</span>
    </div>
  </div>
</template>

<style scoped>
.ranks-page { }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-6);
  gap: var(--space-4);
}

.page-title { font-size: 22px; display: flex; align-items: center; gap: var(--space-2); }
.title-pixel { color: var(--accent); font-size: 16px; }
.page-desc { font-size: 13px; color: var(--text-muted); margin-top: var(--space-1); font-family: var(--font-mono); }

.total-badge {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 2px solid var(--border-strong); background: var(--bg-surface);
  font-family: var(--font-mono); font-size: 12px;
}
.total-label { color: var(--text-muted); }
.total-value { font-weight: 700; color: var(--accent); }

/* ===== 鸟瞰气泡图 ===== */
.birdseye {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: var(--space-8) var(--space-4);
  min-height: 400px;
  background: var(--bg-surface);
  border: 2px solid var(--border);
  position: relative;
}

.bubble {
  border-radius: 50%;
  border: 3px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  cursor: default;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
}

.bubble:hover {
  transform: scale(1.08);
  box-shadow: 0 0 0 4px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.1);
  z-index: 2;
}

.bubble-name {
  font-family: var(--font-body);
  font-weight: 700;
  text-align: center;
  line-height: 1.2;
  padding: 0 8px;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  position: relative;
  z-index: 1;
}

.bubble-tokens {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-muted);
  position: relative;
  z-index: 1;
}

/* ===== 悬浮详情卡 ===== */
.tooltip-card {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
  background: var(--bg-surface);
  border: 2px solid var(--border-strong);
  box-shadow: 6px 6px 0 rgba(26, 26, 26, 0.08);
  padding: 0;
  min-width: 200px;
  max-width: 280px;
}

.tip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-elevated);
  border-bottom: 2px dashed var(--border);
}

.tip-rank {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}

.tip-pos {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
}

.tip-name {
  padding: var(--space-2) var(--space-3) 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.tip-instance {
  padding: 0 var(--space-3);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}

.tip-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  padding: var(--space-2) var(--space-3) var(--space-3);
}

.tip-stat { display: flex; flex-direction: column; gap: 1px; }
.tip-label { font-family: var(--font-mono); font-size: 9px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.tip-value { font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: var(--text-primary); }

.tip-enter-active { transition: opacity 0.1s ease; }
.tip-leave-active { transition: opacity 0.08s ease; }
.tip-enter-from, .tip-leave-to { opacity: 0; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-2); padding: var(--space-16) var(--space-4);
  color: var(--text-muted); font-size: 13px;
}
.empty-pixel { font-size: 32px; opacity: 0.3; }

@media (max-width: 768px) {
  .page-header { flex-direction: column; }
  .page-title { font-size: 18px; }
  .birdseye { padding: var(--space-4); gap: 8px; }
}
</style>
