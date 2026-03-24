<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getRanks } from '../api'
import { useI18n } from '../i18n'

const { t, locale } = useI18n()
const loading = ref(true)
const tiers = ref<any[]>([])
const totalAgents = ref(0)

// 每个官阶的配色方案
const tierColors: Record<number, { bg: string; border: string; text: string }> = {
  0: { bg: '#FFF7E6', border: '#D4A017', text: '#8B6914' },   // 皇帝 - 金色
  1: { bg: '#FFF1F0', border: '#D71921', text: '#A8111A' },   // 一品 - 朱红
  2: { bg: '#F0F5FF', border: '#2F54EB', text: '#1D39C4' },   // 二品 - 靛蓝
  3: { bg: '#F6FFED', border: '#52C41A', text: '#389E0D' },   // 三品 - 翠绿
  4: { bg: '#FFF7E6', border: '#FA8C16', text: '#D46B08' },   // 四品 - 橙色
  5: { bg: '#F9F0FF', border: '#722ED1', text: '#531DAB' },   // 五品 - 紫色
  6: { bg: '#E6FFFB', border: '#13C2C2', text: '#08979C' },   // 六品 - 青色
  7: { bg: '#F0F5FF', border: '#597EF7', text: '#2F54EB' },   // 七品 - 天蓝
  8: { bg: '#FFF0F6', border: '#EB2F96', text: '#C41D7F' },   // 八品 - 粉色
  9: { bg: '#F5F5F5', border: '#8C8C8C', text: '#595959' },   // 九品 - 灰色
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
  return {
    '--tier-bg': c.bg,
    '--tier-border': c.border,
    '--tier-text': c.text,
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

    <div class="tiers-container">
      <section
        v-for="tier in tiers"
        :key="tier.rank_id"
        class="tier-section"
        :style="getTierStyle(tier.rank_id)"
      >
        <div class="tier-header">
          <div class="tier-badge">
            <span class="tier-emoji">{{ tier.rank_emoji }}</span>
            <div class="tier-info">
              <span class="tier-name">{{ getRankName(tier) }}</span>
              <span class="tier-count">{{ tier.agents.length }} Agent{{ tier.agents.length > 1 ? 's' : '' }}</span>
            </div>
          </div>
          <div class="tier-rank-id">
            {{ tier.rank_id === 0 ? '至尊' : (locale === 'en' ? `Rank ${tier.rank_id}` : `${tier.rank_id}品`) }}
          </div>
        </div>

        <div class="agent-cards">
          <div
            v-for="agent in tier.agents"
            :key="agent.instance_id + ':' + agent.agent_id"
            class="agent-card"
          >
            <div class="card-avatar">
              <span class="avatar-emoji">{{ agent.agent_emoji || tier.rank_emoji }}</span>
              <span class="card-position">#{{ agent.position }}</span>
            </div>
            <div class="card-body">
              <div class="card-name">{{ agent.agent_name }}</div>
              <div class="card-stats">
                <span class="stat-item">
                  <span class="stat-icon" aria-hidden="true">◆</span>
                  {{ formatTokens(agent.total_tokens) }} tokens
                </span>
                <span class="stat-item">
                  <span class="stat-icon" aria-hidden="true">◇</span>
                  {{ agent.session_count }} {{ t('ranks.sessions') }}
                </span>
              </div>
            </div>
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
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 2px solid var(--border-strong);
  background: var(--bg-surface);
  font-family: var(--font-mono);
  font-size: 12px;
}
.total-label { color: var(--text-muted); }
.total-value { font-weight: 700; color: var(--accent); }

.tiers-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.tier-section {
  background: var(--bg-surface);
  border: 2px solid var(--tier-border);
  overflow: hidden;
}

.tier-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--tier-bg);
  border-bottom: 2px dashed var(--tier-border);
}

.tier-badge { display: flex; align-items: center; gap: var(--space-3); }

.tier-emoji {
  font-size: 28px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--tier-border);
  background: var(--bg-surface);
}

.tier-info { display: flex; flex-direction: column; gap: 2px; }
.tier-name { font-size: 16px; font-weight: 700; color: var(--tier-text); }
.tier-count { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }

.tier-rank-id {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--tier-text);
  padding: var(--space-1) var(--space-2);
  border: 2px solid var(--tier-border);
  background: var(--bg-surface);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.agent-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-3);
  padding: var(--space-4);
}

.agent-card {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 2px solid var(--border);
  background: var(--bg-surface);
  transition: all var(--duration-fast) ease;
}

.agent-card:hover {
  border-color: var(--tier-border);
  transform: translateY(-1px);
  box-shadow: 3px 3px 0 var(--tier-bg);
}

.card-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.avatar-emoji {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--border);
  background: var(--bg-elevated);
}

.card-position {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
}

.card-body { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 4px; }

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-stats { display: flex; gap: var(--space-3); flex-wrap: wrap; }

.stat-item {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-icon { font-size: 8px; color: var(--tier-border); }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-16) var(--space-4);
  color: var(--text-muted);
  font-size: 13px;
}
.empty-pixel { font-size: 32px; opacity: 0.3; }

@media (max-width: 768px) {
  .page-header { flex-direction: column; }
  .page-title { font-size: 18px; }
  .agent-cards { grid-template-columns: 1fr; }
}
</style>
