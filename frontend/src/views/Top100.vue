<template>
  <div>
    <!-- 头部 -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">成交额前100</h2>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-500">日期：</label>
        <input
          type="date"
          v-model="selectedDate"
          @change="loadData"
          class="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>
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
import { getTop100 } from '../api'
import StockTable from '../components/StockTable.vue'

const columns = [
  { key: 'rank', label: '排名', align: 'left' },
  { key: 'stock_code', label: '股票代码', align: 'left' },
  { key: 'stock_name', label: '股票名称', align: 'left' },
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

async function loadData() {
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

onMounted(loadData)
</script>
