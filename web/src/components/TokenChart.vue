<script setup lang="ts">
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { computed } from 'vue'
import { useI18n } from '../i18n'

use([CanvasRenderer, LineChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const { t } = useI18n()

const props = defineProps<{
  title?: string
  data: Array<{ hour: string; input_tokens: number; output_tokens: number; total_tokens: number }>
  type?: 'line' | 'bar'
}>()

const option = computed(() => ({
  title: props.title ? {
    text: props.title,
    left: 'center',
    textStyle: {
      fontSize: 12,
      fontFamily: 'Silkscreen, cursive',
      fontWeight: 400,
      color: '#888888',
    },
  } : undefined,
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#FFFFFF',
    borderColor: '#1A1A1A',
    borderWidth: 2,
    textStyle: {
      color: '#1A1A1A',
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 11,
    },
    formatter: (params: any) => {
      let html = `<div style="font-size:10px;color:#888;margin-bottom:4px;font-family:Silkscreen,cursive">${params[0]?.axisValue || ''}</div>`
      for (const p of params) {
        html += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0">
          <span style="display:inline-block;width:8px;height:8px;background:${p.color}"></span>
          <span style="color:#555">${p.seriesName}:</span>
          <span style="color:#1A1A1A;font-weight:600">${(p.value || 0).toLocaleString()}</span>
        </div>`
      }
      return html
    },
  },
  legend: {
    bottom: 0,
    textStyle: {
      color: '#888888',
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 10,
    },
    itemWidth: 12,
    itemHeight: 4,
    itemGap: 20,
  },
  grid: {
    left: 56,
    right: 16,
    top: props.title ? 40 : 16,
    bottom: 40,
  },
  xAxis: {
    type: 'category',
    data: props.data.map(d => {
      const date = new Date(d.hour)
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:00`
    }),
    axisLabel: {
      fontSize: 9,
      rotate: 30,
      color: '#888888',
      fontFamily: 'JetBrains Mono, monospace',
    },
    axisLine: { lineStyle: { color: '#D9D5CF' } },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      color: '#888888',
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 10,
      formatter: (v: number) => {
        if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M'
        if (v >= 1000) return (v / 1000).toFixed(0) + 'K'
        return v.toString()
      },
    },
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#E5E1DB', type: 'dashed' } },
  },
  series: [
    {
      name: t('chart.inputTokens'),
      type: props.type || 'line',
      data: props.data.map(d => d.input_tokens),
      smooth: false,
      step: false,
      symbol: 'rect',
      symbolSize: 6,
      lineStyle: { width: 2, color: '#D71921' },
      itemStyle: { color: '#D71921' },
      areaStyle: props.type !== 'bar' ? {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(215, 25, 33, 0.1)' },
            { offset: 1, color: 'rgba(215, 25, 33, 0)' },
          ],
        },
      } : undefined,
    },
    {
      name: t('chart.outputTokens'),
      type: props.type || 'line',
      data: props.data.map(d => d.output_tokens),
      smooth: false,
      symbol: 'rect',
      symbolSize: 6,
      lineStyle: { width: 2, color: '#1B873F' },
      itemStyle: { color: '#1B873F' },
      areaStyle: props.type !== 'bar' ? {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(27, 135, 63, 0.08)' },
            { offset: 1, color: 'rgba(27, 135, 63, 0)' },
          ],
        },
      } : undefined,
    },
    {
      name: t('chart.totalTokens'),
      type: props.type || 'line',
      data: props.data.map(d => d.total_tokens),
      smooth: false,
      symbol: 'rect',
      symbolSize: 6,
      lineStyle: { width: 2, color: '#1A1A1A' },
      itemStyle: { color: '#1A1A1A' },
    },
  ],
}))
</script>

<template>
  <v-chart :option="option" style="height: 100%; width: 100%" autoresize />
</template>
