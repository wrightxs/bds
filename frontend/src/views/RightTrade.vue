<template>
  <div>
    <!-- 头部 -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold text-gray-800">右侧交易</h2>
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

    <!-- 周期切换 -->
    <div class="flex items-center gap-2 mb-4">
      <span class="text-sm text-gray-500">统计周期：</span>
      <button
        v-for="d in periodOptions"
        :key="d"
        class="px-4 py-1.5 text-sm rounded-md border transition-colors"
        :class="activeDays === d
          ? 'bg-blue-500 text-white border-blue-500'
          : 'border-gray-300 text-gray-600 hover:bg-gray-50'"
        @click="switchDays(d)"
      >{{ d }}天</button>
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
        :data="data"
        :sort-key="sortKey"
        :sort-dir="sortDir"
        @sort="handleSort"
      />
      <div class="px-4 py-2 text-xs text-gray-400 border-t">
        近 {{ activeDays }} 个交易日，筛选出 {{ data.length }} 只
        <span v-if="displayDate" class="ml-2">{{ displayDate }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getRightTrade, getDates } from '../api'
import StockTable from '../components/StockTable.vue'
import { isQueryingToday } from '../utils/date'

const columns = [
  { key: 'stock_code', label: '股票代码', align: 'left' },
  { key: 'stock_name', label: '股票名称', align: 'left' },
  { key: 'low_date', label: '低点日期', align: 'left' },
  { key: 'low_price', label: '低点价格', align: 'right', format: 'price' },
  { key: 'high_price', label: '最高价', align: 'right', format: 'price' },
  { key: 'max_rise_pct', label: '最大涨幅', align: 'right', format: 'pct' },
  { key: 'current_close', label: '当前价', align: 'right', format: 'price' },
  { key: 'from_low_pct', label: '距低点涨幅', align: 'right', format: 'pct' },
]

const periodOptions = [10, 20, 30]

const loading = ref(true)
const error = ref(null)
const selectedDate = ref('')
const displayDate = ref('')
const activeDays = ref(10)
const data = ref([])
const sortKey = ref('max_rise_pct')
const sortDir = ref('desc')
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

async function fetchDates() {
  try {
    const res = await getDates()
    availableDates.value = res.data.dates || []
  } catch (e) {
    // 静默失败
  }
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

function switchDays(days) {
  activeDays.value = days
  loadData()
}

function handleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'desc'
  }
}

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const res = await getRightTrade(activeDays.value, selectedDate.value || undefined)
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
  fetchDates()
  loadData()
})
</script>
