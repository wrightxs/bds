<template>
  <div>
    <!-- 头部 -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">成交额前100</h2>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-500">日期：</label>
        <button
          class="px-2 py-1.5 text-sm rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="!hasPrev"
          @click="goPrevDay"
          title="上一天"
        >←</button>
        <input
          type="date"
          v-model="selectedDate"
          @change="loadData"
          class="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          class="px-2 py-1.5 text-sm rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="!hasNext"
          @click="goNextDay"
          title="下一天"
        >→</button>
      </div>
    </div>

    <!-- 查询中提示 -->
    <div
      v-if="showQuerying && !loading && !error"
      class="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 flex items-center gap-3"
    >
      <span class="text-yellow-600 text-base">⚠</span>
      <span class="text-sm text-yellow-700 flex-1">当日数据尚未生成，系统将在交易日 18:00 自动抓取</span>
    </div>

    <!-- 加载 -->
    <div v-if="loading" class="text-center py-20 text-gray-400">加载中...</div>
    <div v-else-if="error" class="text-center py-20 text-red-400">{{ error }}</div>

    <!-- 表格 -->
    <div v-else class="bg-white rounded-lg shadow-sm border border-gray-200">
      <StockTable
        :columns="columns"
        :data="sortedData"
        :sort-key="sortKey"
        :sort-dir="sortDir"
        @sort="handleSort"
      />
      <div class="px-4 py-2 text-xs text-gray-400 border-t">
        共 {{ sortedData.length }} 条记录
        <span v-if="displayDate" class="ml-2">{{ displayDate }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getTop100, getDates } from '../api'
import StockTable from '../components/StockTable.vue'
import { isQueryingToday, wasFetchedToday, markFetchedToday } from '../utils/date'

const columns = [
  { key: 'rank', label: '排名', align: 'left' },
  { key: 'stock_code', label: '股票代码', align: 'left' },
  { key: 'stock_name', label: '股票名称', align: 'left' },
  { key: 'industry', label: '行业板块', align: 'left' },
  { key: 'close', label: '收盘价', align: 'right', format: 'price' },
  { key: 'amount', label: '成交额', align: 'right', format: 'amount' },
  { key: 'pct_change', label: '涨跌幅', align: 'right', format: 'pct' },
]

const loading = ref(true)
const error = ref(null)
const selectedDate = ref('')
const displayDate = ref('')
const data = ref([])
const sortKey = ref('rank')
const sortDir = ref('asc')
const availableDates = ref([])

const showQuerying = computed(() => {
  return isQueryingToday(displayDate.value, selectedDate.value)
})

const dateIndex = computed(() => {
  return availableDates.value.indexOf(displayDate.value || selectedDate.value)
})

const hasPrev = computed(() => {
  const idx = dateIndex.value
  return idx >= 0 && idx < availableDates.value.length - 1
})

const hasNext = computed(() => {
  const idx = dateIndex.value
  return idx > 0
})

const sortedData = computed(() => {
  const arr = [...data.value]
  arr.sort((a, b) => {
    const va = a[sortKey.value] ?? 0
    const vb = b[sortKey.value] ?? 0
    const dir = sortDir.value === 'asc' ? 1 : -1
    if (typeof va === 'string') return va.localeCompare(vb) * dir
    return (Number(va) - Number(vb)) * dir
  })
  return arr
})

function handleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'desc'
  }
}

async function fetchDates() {
  if (wasFetchedToday()) return
  try {
    const res = await getDates()
    availableDates.value = res.data.dates || []
    markFetchedToday()
  } catch (e) {}
}

function goPrevDay() {
  const idx = dateIndex.value
  if (idx >= 0 && idx < availableDates.value.length - 1) {
    selectedDate.value = availableDates.value[idx + 1]
    loadData()
  }
}

function goNextDay() {
  const idx = dateIndex.value
  if (idx > 0) {
    selectedDate.value = availableDates.value[idx - 1]
    loadData()
  }
}

async function loadData() {
  await fetchDates()
  loading.value = true
  error.value = null
  try {
    const res = await getTop100(selectedDate.value || undefined)
    data.value = res.data.data
    displayDate.value = res.data.date
    if (!selectedDate.value && res.data.date) {
      selectedDate.value = res.data.date
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
