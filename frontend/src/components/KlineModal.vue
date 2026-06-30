<template>
  <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center" @click.self="close">
    <div class="bg-white rounded-lg shadow-2xl w-[900px] max-h-[90vh] overflow-auto">
      <div class="flex items-center justify-between px-5 py-3 border-b">
        <h3 class="text-lg font-semibold text-gray-800">
          {{ stockName }} <span class="text-sm text-gray-400 font-normal">{{ stockCode }}</span>
        </h3>
        <button @click="close" class="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      <div class="p-4">
        <div v-if="loading" class="text-center py-20 text-gray-400">加载中...</div>
        <div v-else-if="error" class="text-center py-20 text-red-400">{{ error }}</div>
        <div v-show="!loading && !error" ref="chartRef" style="width: 100%; height: 500px;"></div>
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
    // 使用国内 CDN 镜像
    script.src = 'https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js'
    script.onload = () => resolve(window.echarts)
    script.onerror = () => {
      // 回退到 jsdelivr
      const s2 = document.createElement('script')
      s2.src = 'https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'
      s2.onload = () => resolve(window.echarts)
      s2.onerror = () => reject(new Error('ECharts 加载失败'))
      document.head.appendChild(s2)
    }
    document.head.appendChild(script)
  })
}

watch(() => props.visible, async (v) => {
  if (!v) return
  loading.value = true
  error.value = null
  await nextTick()  // 等待 v-if 的 DOM 创建完成
  if (!chartRef.value) { loading.value = false; return }

  try {
    const [echarts, res] = await Promise.all([loadECharts(), getKline(props.stockCode, 60)])
    const raw = res.data.data
    if (!raw.length) { error.value = '无数据'; loading.value = false; return }

    const dates = raw.map(r => r.date)
    const ohlc = raw.map(r => [r.open, r.close, r.low, r.high])
    const volumes = raw.map(r => r.volume)
    const closes = raw.map(r => r.close)
    const ma5 = calcMA(closes, 5)
    const ma10 = calcMA(closes, 10)
    const ma20 = calcMA(closes, 20)

    if (chart) { chart.dispose(); chart = null }
    chart = echarts.init(chartRef.value)
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: [
        { left: '10%', right: '3%', top: '3%', height: '58%' },
        { left: '10%', right: '3%', top: '72%', height: '18%' },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, boundaryGap: true },
        { type: 'category', data: dates, gridIndex: 1, boundaryGap: true },
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, scale: true, splitArea: { show: true } },
        { type: 'value', gridIndex: 1, scale: true, splitNumber: 2 },
      ],
      series: [
        {
          name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
          itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' },
        },
        { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1, color: '#f59e0b' }, symbol: 'none' },
        { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1, color: '#3b82f6' }, symbol: 'none' },
        { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1, color: '#8b5cf6' }, symbol: 'none' },
        {
          name: '量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
          itemStyle: { color: (p) => raw[p.dataIndex]?.close >= raw[p.dataIndex]?.open ? '#ef4444' : '#22c55e' },
        },
      ],
    })
    loading.value = false
  } catch (e) {
    error.value = e.message || '加载失败'
    loading.value = false
  }
})

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

onBeforeUnmount(() => { if (chart) { chart.dispose(); chart = null } })
</script>
