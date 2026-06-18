<template>
  <div>
    <!-- 头部 -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold text-gray-800">涨停股票</h2>
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

    <!-- 板块筛选 -->
    <div class="mb-4">
      <BoardFilter
        v-model="activeBoard"
        :options="boardOptions"
        @select="handleBoardSelect"
      />
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
        共 {{ data.length }} 只涨停股票
        <span v-if="displayDate" class="ml-2">{{ displayDate }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getLimitUp } from '../api'
import StockTable from '../components/StockTable.vue'
import BoardFilter from '../components/BoardFilter.vue'

const columns = [
  { key: 'stock_code', label: '股票代码', align: 'left' },
  { key: 'stock_name', label: '股票名称', align: 'left' },
  { key: 'board_label', label: '板块', align: 'left' },
  { key: 'limit_up_price', label: '涨停价', align: 'right', format: 'price' },
  { key: 'pct_change', label: '涨跌幅', align: 'right', format: 'pct' },
  { key: 'consecutive', label: '连板', align: 'center' },
]

const boardOptions = [
  { value: '', label: '全部' },
  { value: 'main', label: '主板' },
  { value: 'chi_next', label: '创业板' },
  { value: 'star', label: '科创板' },
  { value: 'bse', label: '北交所' },
]

const loading = ref(true)
const error = ref(null)
const selectedDate = ref('')
const displayDate = ref('')
const activeBoard = ref('')
const data = ref([])
const sortKey = ref('consecutive')
const sortDir = ref('desc')

function handleBoardSelect(board) {
  activeBoard.value = board
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
    const board = activeBoard.value || undefined
    const res = await getLimitUp(selectedDate.value || undefined, board)
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
