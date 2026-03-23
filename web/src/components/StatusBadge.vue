<script setup lang="ts">
defineProps<{
  status: string
}>()

const themeMap: Record<string, { color: string; bg: string; border: string }> = {
  online:    { color: 'var(--green)',  bg: 'var(--green-light)',  border: 'var(--green)' },
  offline:   { color: 'var(--red)',    bg: 'var(--red-light)',    border: 'var(--red)' },
  unhealthy: { color: 'var(--amber)',  bg: 'var(--amber-light)',  border: 'var(--amber)' },
  running:   { color: 'var(--accent)', bg: 'var(--accent-light)', border: 'var(--accent)' },
  done:      { color: 'var(--green)',  bg: 'var(--green-light)',  border: 'var(--green)' },
  failed:    { color: 'var(--red)',    bg: 'var(--red-light)',    border: 'var(--red)' },
  killed:    { color: 'var(--red)',    bg: 'var(--red-light)',    border: 'var(--red)' },
  timeout:   { color: 'var(--amber)',  bg: 'var(--amber-light)',  border: 'var(--amber)' },
}

const getTheme = (status: string) => themeMap[status] || { color: 'var(--text-muted)', bg: 'var(--bg-elevated)', border: 'var(--border)' }
</script>

<template>
  <span
    class="status-badge"
    :style="{
      color: getTheme(status).color,
      background: getTheme(status).bg,
      borderColor: getTheme(status).border,
    }"
  >
    <span
      class="status-pixel"
      :class="{ blink: status === 'online' || status === 'running' }"
      :style="{ background: getTheme(status).color }"
    ></span>
    {{ status }}
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px 2px 6px;
  border: 2px solid;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  white-space: nowrap;
  line-height: 1.6;
}

.status-pixel {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
}

.status-pixel.blink {
  animation: pixel-blink 1.5s step-end infinite;
}

@keyframes pixel-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
