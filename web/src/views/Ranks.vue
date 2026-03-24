<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getRanks } from '../api'
import { useI18n } from '../i18n'

const { t, locale } = useI18n()
const loading = ref(true)
const tiers = ref<any[]>([])
const totalAgents = ref(0)

const tierColors: Record<number, { bg: string; border: string; text: string }> = {
  0: { bg: '#FFF7E6', border: '#D4A017', text: '#8B6914' },
  1: { bg: '#FFF1F0', border: '#D71921', text: '#A8111A' },
  2: { bg: '#F0F5FF', border: '#2F54EB', text: '#1D39C4' },
  3: { bg: '#F6FFED', border: '#52C41A', text: '#389E0D' },
  4: { bg: '#FFF7E6', border: '#FA8C16', text: '#D46B08' },
  5: { bg: '#F9F0FF', border: '#722ED1', text: '#531DAB' },
  6: { bg: '#E6FFFB', border: '#13C2C2', text: '#08979C' },
  7: { bg: '#F0F5FF', border: '#597EF7', text: '#2F54EB' },
  8: { bg: '#FFF0F6', border: '#EB2F96', text: '#C41D7F' },
  9: { bg: '#F5F5F5', border: '#8C8C8C', text: '#595959' },
}

// 根据官阶等级返回尺寸缩放因子
const tierScale = (rankId: number) => {
  const scales: Record<number, { emoji: number; card: number; name: number; avatar: number }> = {
    0: { emoji: 48, card: 320, name: 18, avatar: 56 },
    1: { emoji: 40, card: 300, name: 16, avatar: 48 },
    2: { emoji: 36, card: 280, name: 15, avatar: 44 },
    3: { emoji: 32, card: 260, name: 14, avatar: 40 },
    4: { emoji: 28, card: 240, name: 13, avatar: 38 },
    5: { emoji: 26, card: 230, name: 13, avatar: 36 },
    6: { emoji: 24, card: 220, name: 12, avatar: 34 },
    7: { emoji: 22, card: 210, name: 12, avatar: 32 },
    8: { emoji: 20, card: 200, name: 11, avatar: 30 },
    9: { emoji: 18, card: 190, name: 11, avatar: 28 },
  }
  return scales[rankId] || scales[9]
}

const formatTokens = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

const getRankName = (tier: any) => {
  return locale.value === 'en' ? tier.rank_name_en : tier.rank_name
}

const getTierStyle = (rankId: number) => {
  const c = tierColors[rankId] || tierColors[9]
  const s = tierScale(rankId)
  return {
    '--tier-bg': c.bg,
    '--tier-border': c.border,
    '--tier-text': c.text,
    '--tier-emoji-size': s.emoji + 'px',
    '--tier-card-min': s.card + 'px',
    '--tier-name-size': s.name + 'px',
    '--tier-avatar-size': s.avatar + 'px',
  }
}

onMounted(async () => {
  try {
    const res = await getRanks()
    tiers.value = res.data.tiers
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

    <div class="pyramid">
      <section
        v-for="tier in tiers"
        :key="tier.rank_id"
        class="tier-section"
        :class="'tier-' + tier.rank_id"
        :style="getTierStyle(tier.rank_id)"
      >
        <!-- 官阶头部 -->
        <div class="tier-header">
          <span class="tier-header-emoji">{{ tier.rank_emoji }}</span>
          <span class="tier-header-name">{{ getRankName(tier) }}</span>
          <span class="tier-header-count">{{ tier.agents.length }}</span>
        </div>

        <!-- Agent 卡片网格 — 居中对齐形成金字塔 -->
        <div class="agent-cards">
          <div
            v-for="agent in tier.agents"
            :key="agent.instance_id + ':' + agent.agent_id"
            class="agent-card"
          >
            <div class="card-body">
              <div class="card-name" :title="agent.agent_name">{{ agent.agent_name }}</div>
              <div class="card-instance">{{ agent.instance_name }}</div>
              <div class="card-stats">
                <span class="stat-token">{{ formatTokens(agent.total_tokens) }}</span>
                <span class="stat-sep">·</span>
                <span class="stat-session">{{ agent.session_count }} {{ t('ranks.sessions') }}</span>
              </div>
            </div>
            <div class="card-rank">#{{ agent.position }}</div>
          </div>
        </div>
      </section>

      <div v-if="!loading && tiers.length === 0" class="empty-state" role="status">
        <span class="empty-pixel" aria-hidden="true">□</span>
        <span>{{ t('ranks.empty') }}</span>
      </div>
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

/* ===== 金字塔布局 ===== */
.pyramid {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.tier-section {
  width: 100%;
  background: var(--bg-surface);
  border: 2px solid var(--tier-border);
  overflow: hidden;
}

/* 金字塔宽度递增 */
.tier-0 { max-width: 400px; }
.tier-1 { max-width: 520px; }
.tier-2 { max-width: 640px; }
.tier-3 { max-width: 760px; }
.tier-4 { max-width: 860px; }
.tier-5 { max-width: 940px; }
.tier-6 { max-width: 1000px; }
.tier-7 { max-width: 1060px; }
.tier-8 { max-width: 1100px; }
.tier-9 { max-width: 100%; }

/* 官阶头部 */
.tier-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--tier-bg);
  border-bottom: 2px dashed var(--tier-border);
}

.tier-header-emoji { font-size: var(--tier-emoji-size); line-height: 1; }

.tier-header-name {
  font-family: var(--font-body);
  font-size: var(--tier-name-size);
  font-weight: 700;
  color: var(--tier-text);
}

.tier-header-count {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--tier-text);
  padding: 1px 6px;
  border: 1px solid var(--tier-border);
  background: var(--bg-surface);
  opacity: 0.7;
}

/* Agent 卡片网格 — 居中对齐 */
.agent-cards {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-3);
}

.agent-card {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 2px solid var(--border);
  background: var(--bg-surface);
  min-width: var(--tier-card-min);
  max-width: 360px;
  flex: 0 1 auto;
  transition: all var(--duration-fast) ease;
}

.agent-card:hover {
  border-color: var(--tier-border);
  transform: translateY(-1px);
  box-shadow: 3px 3px 0 var(--tier-bg);
}

.card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-name {
  font-family: var(--font-body);
  font-size: var(--tier-name-size);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-instance {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-stats {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
}

.stat-token { color: var(--tier-text); font-weight: 600; }
.stat-sep { color: var(--text-muted); }
.stat-session { color: var(--text-muted); }

.card-rank {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--tier-text);
  opacity: 0.6;
}

.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-2); padding: var(--space-16) var(--space-4);
  color: var(--text-muted); font-size: 13px;
}
.empty-pixel { font-size: 32px; opacity: 0.3; }

@media (max-width: 768px) {
  .page-header { flex-direction: column; }
  .page-title { font-size: 18px; }
  .tier-0, .tier-1, .tier-2, .tier-3, .tier-4,
  .tier-5, .tier-6, .tier-7, .tier-8, .tier-9 { max-width: 100%; }
  .agent-card { min-width: 0; max-width: 100%; flex: 1 1 100%; }
}
</style>
