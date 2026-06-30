<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center" @click.self="close">
    <div class="bg-white rounded-lg shadow-2xl w-[900px] max-h-[90vh] overflow-auto">
      <!-- 头部 -->
      <div class="flex items-center justify-between px-5 py-3 border-b">
        <h3 class="text-lg font-semibold text-gray-800">
          {{ stockName }} <span class="text-sm text-gray-400 font-normal">{{ stockCode }}</span>
        </h3>
        <button @click="close" class="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      <!-- 图表 -->
      <div class="p-4">
        <div v-if="loading" class="text-center py-20 text-gray-400">加载中...</div>
        <div v-else-if="error" class="text-center py-20 text-red-400">{{ error }}</div>
        <div v-else ref="chartRef" style="height: 500px;"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { getKline } from '../api'

const props = defineProps({
  stockCode: String,
  stockName: String,
  visible: Boolean,
})
const emit = defineEmits(['close'])

const chartRef = ref(null)
const loading = ref(false)
const error = ref(null)
let chart = null

function close() { emit('close') }

async function loadECharts() {
  if (window.echarts) return window.echarts
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'
    script.onload = () => resolve(window.echarts)
    script.onerror = reject
    document.head.appendChild(script)
  })
}

async function render() {
  loading.value = true; error.value = null
  try {
    const [echarts, res] = await Promise.all([loadECharts(), getKline(props.stockCode, 60)])
    const raw = res.data.data
    if (!raw.length) { error.value = '无数据'; return }

    const dates = raw.map(r => r.date)
    const ohlc = raw.map(r => [r.open, r.close, r.low, r.high])
    const volumes = raw.map(r => r.volume)
    const ma5 = calcMA(raw.map(r => r.close), 5)
    const ma10 = calcMA(raw.map(r => r.close), 10)
    const ma20 = calcMA(raw.map(r => r.close), 20)

    await nextTick()
    if (!chartRef.value) return
    if (chart) chart.dispose()
    chart = echarts.init(chartRef.value)

    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: [
        { left: '8%', right: '8%', top: '5%', height: '60%' },
        { left: '8%', right: '8%', top: '75%', height: '15%' },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false } },
        { type: 'category', data: dates, gridIndex: 1 },
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, scale: true },
        { type: 'value', gridIndex: 1, scale: true, splitNumber: 2 },
      ],
      series: [
        { name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
          itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' } },
        { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1 }, symbol: 'none' },
        { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1 }, symbol: 'none' },
        { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1 }, symbol: 'none' },
        { name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
          itemStyle: { color: (p) => raw[p.dataIndex]?.close >= raw[p.dataIndex]?.open ? '#ef4444' : '#22c55e' } },
      ],
    })
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally { loading.value = false }
}

function calcMA(data, period) {
  const result = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(null); continue }
    let sum = 0
    for (let j = 0; j < period; j++) sum += data[i - j]
    result.push(+(sum / period).toFixed(2))
  }
  return result
}

watch(() => props.visible, (v) => { if (v) render() })
onBeforeUnmount(() => { if (chart) chart.dispose() })
</script>
