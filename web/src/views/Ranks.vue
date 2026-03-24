<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { getRanks } from '../api'
import { useI18n } from '../i18n'

const { t } = useI18n()
const loading = ref(true)
const allAgents = ref<any[]>([])
const totalAgents = ref(0)
const hoveredAgent = ref<any>(null)
const tooltipPos = ref({ x: 0, y: 0 })
const containerRef = ref<HTMLElement | null>(null)
const containerSize = ref({ w: 800, h: 600 })

const palette = [
  '#D71921', '#2F54EB', '#1B873F', '#FA8C16', '#722ED1',
  '#13C2C2', '#EB2F96', '#D4A017', '#597EF7', '#52C41A',
  '#C27803', '#08979C', '#531DAB', '#A8111A', '#1D39C4',
  '#389E0D', '#D46B08', '#C41D7F', '#8B6914', '#595959',
]

const getColor = (idx: number) => palette[idx % palette.length]

// 简单的圆圈碰撞检测放置算法
const layoutBubbles = (agents: any[], w: number, h: number) => {
  if (agents.length === 0) return []

  const tokens = agents.map(a => a.total_tokens || 1)
  const maxT = Math.max(...tokens)
  const minT = Math.min(...tokens)
  const range = maxT - minT || 1

  // 按 token 从大到小排列，大圆先放置
  const sorted = agents.map((agent, idx) => {
    const ratio = (agent.total_tokens - minT) / range
    const size = 60 + Math.sqrt(ratio) * 140
    return { ...agent, size, color: getColor(idx), idx }
  }).sort((a, b) => b.size - a.size)

  const placed: { x: number; y: number; r: number }[] = []
  const result: any[] = []
  const cx = w / 2
  const cy = h / 2

  for (const bubble of sorted) {
    const r = bubble.size / 2
    let bestX = cx
    let bestY = cy
    let found = false

    // 从中心向外螺旋搜索不重叠的位置
    for (let attempt = 0; attempt < 500; attempt++) {
      const angle = attempt * 0.5 + Math.random() * 0.3
      const dist = attempt * 3 + Math.random() * 20
      const tx = cx + Math.cos(angle) * dist
      const ty = cy + Math.sin(angle) * dist

      // 边界检查
      if (tx - r < 0 || tx + r > w || ty - r < 0 || ty + r > h) continue

      // 碰撞检查
      let collides = false
      for (const p of placed) {
        const dx = tx - p.x
        const dy = ty - p.y
        const minDist = r + p.r + 6 // 6px 间距
        if (dx * dx + dy * dy < minDist * minDist) {
          collides = true
          break
        }
      }

      if (!collides) {
        bestX = tx
        bestY = ty
        found = true
        break
      }
    }

    // 如果没找到完美位置，用随机偏移
    if (!found) {
      bestX = cx + (Math.random() - 0.5) * (w - bubble.size)
      bestY = cy + (Math.random() - 0.5) * (h - bubble.size)
      bestX = Math.max(r, Math.min(w - r, bestX))
      bestY = Math.max(r, Math.min(h - r, bestY))
    }

    placed.push({ x: bestX, y: bestY, r })
    result.push({ ...bubble, x: bestX - r, y: bestY - r })
  }

  return result
}

const bubbles = computed(() => {
  return layoutBubbles(allAgents.value, containerSize.value.w, containerSize.value.h)
})

// 计算容器需要的高度
const containerHeight = computed(() => {
  const count = allAgents.value.length
  if (count <= 3) return 400
  if (count <= 10) return 500
  return Math.min(800, 400 + count * 20)
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

const updateContainerSize = () => {
  if (containerRef.value) {
    containerSize.value = {
      w: containerRef.value.clientWidth,
      h: containerRef.value.clientHeight,
    }
  }
}

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  try {
    const res = await getRanks()
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

  await nextTick()
  updateContainerSize()
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(updateContainerSize)
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
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

    <div
      ref="containerRef"
      class="birdseye"
      :style="{ height: containerHeight + 'px' }"
    >
      <div
        v-for="b in bubbles"
        :key="b.instance_id + ':' + b.agent_id"
        class="bubble"
        :style="{
          width: b.size + 'px',
          height: b.size + 'px',
          left: b.x + 'px',
          top: b.y + 'px',
          borderColor: b.color,
          backgroundColor: b.color + '12',
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

    <Teleport to="body">
      <Transition name="tip">
        <div
          v-if="hoveredAgent"
          class="tooltip-card"
          :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
        >
          <div class="tip-header" :style="{ borderBottomColor: hoveredAgent.color }">
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

/* ===== 鸟瞰图 ===== */
.birdseye {
  position: relative;
  background: var(--bg-surface);
  border: 2px solid var(--border);
  overflow: hidden;
}

.bubble {
  position: absolute;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  cursor: default;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-width 0.15s ease;
  overflow: hidden;
}

.bubble:hover {
  transform: scale(1.06);
  box-shadow: 0 0 20px rgba(0,0,0,0.08);
  border-width: 3px;
  z-index: 2;
}

.bubble-name {
  font-family: var(--font-body);
  font-weight: 700;
  text-align: center;
  line-height: 1.2;
  padding: 0 6px;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bubble-tokens {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-muted);
}

/* ===== Tooltip ===== */
.tooltip-card {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
  background: var(--bg-surface);
  border: 2px solid var(--border-strong);
  box-shadow: 6px 6px 0 rgba(26, 26, 26, 0.08);
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

.tip-rank { font-family: var(--font-body); font-size: 12px; font-weight: 700; color: var(--text-primary); }
.tip-pos { font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-muted); }

.tip-name {
  padding: var(--space-2) var(--space-3) 0;
  font-size: 14px; font-weight: 700; color: var(--text-primary);
}

.tip-instance {
  padding: 0 var(--space-3);
  font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);
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
}
</style>
