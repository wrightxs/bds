<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">缠论</h2>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-500">日期：</label>
        <button
          class="px-2 py-1.5 text-sm rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="!hasPrev" @click="goPrevDay" title="上一天"
        >←</button>
        <input type="date" v-model="selectedDate" @change="loadData"
          class="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <button
          class="px-2 py-1.5 text-sm rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="!hasNext" @click="goNextDay" title="下一天"
        >→</button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-20 text-gray-400">加载中...</div>
    <div v-else-if="error" class="text-center py-20 text-red-400">{{ error }}</div>

    <template v-else>
      <!-- 买卖点切换 -->
      <div class="flex items-center gap-2 mb-4">
        <span class="text-sm text-gray-500">信号类型：</span>
        <button
          v-for="t in buyTypes"
          :key="t.key"
          class="px-4 py-1.5 text-sm rounded-md border transition-colors"
          :class="activeBuy === t.key
            ? 'bg-blue-500 text-white border-blue-500'
            : 'border-gray-300 text-gray-600 hover:bg-gray-50'"
          @click="activeBuy = t.key"
        >{{ t.label }} · {{ t.count }} 只</button>
      </div>

      <div class="bg-white rounded-lg shadow-sm border border-gray-200">
        <StockTable :columns="activeColumns" :data="activeData" :sort-key="sortKey" :sort-dir="sortDir" @sort="handleSort" />
        <div v-if="!activeData.length" class="px-4 py-8 text-center text-gray-400">暂无符合条件</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getChanTheory, getDates } from '../api'
import StockTable from '../components/StockTable.vue'
import { wasFetchedToday, markFetchedToday } from '../utils/date'

const columns1 = [
  { key: 'stock_code', label: '股票代码', align: 'left' },
  { key: 'stock_name', label: '股票名称', align: 'left' },
  { key: 'close', label: '收盘价', align: 'right', format: 'price' },
  { key: 'low_price', label: '低点价格', align: 'right', format: 'price' },
  { key: 'low_date', label: '低点日期', align: 'left' },
  { key: 'rebound_pct', label: '反弹涨幅', align: 'right', format: 'pct' },
  { key: 'amount', label: '成交额', align: 'right', format: 'amount' },
]

const columns2 = [
  { key: 'stock_code', label: '股票代码', align: 'left' },
  { key: 'stock_name', label: '股票名称', align: 'left' },
  { key: 'close', label: '收盘价', align: 'right', format: 'price' },
  { key: 'prev_low', label: '前期低点', align: 'right', format: 'price' },
  { key: 'prev_low_date', label: '前低日期', align: 'left' },
  { key: 'pullback_low', label: '回踩低点', align: 'right', format: 'price' },
  { key: 'rebound_pct', label: '累计涨幅', align: 'right', format: 'pct' },
  { key: 'amount', label: '成交额', align: 'right', format: 'amount' },
]

const loading = ref(true)
const error = ref(null)
const selectedDate = ref('')
const buy1 = ref([])
const buy2 = ref([])
const activeBuy = ref('buy2')
const sortKey = ref('rebound_pct')
const sortDir = ref('desc')
const availableDates = ref([])

const buyTypes = computed(() => [
  { key: 'buy1', label: '1买（底部背驰反转）', count: buy1.value.length },
  { key: 'buy2', label: '2买（回踩不破前低）', count: buy2.value.length },
])

const activeColumns = computed(() => activeBuy.value === 'buy1' ? columns1 : columns2)
const activeData = computed(() => activeBuy.value === 'buy1' ? buy1.value : buy2.value)

const dateIndex = computed(() => availableDates.value.indexOf(selectedDate.value))
const hasPrev = computed(() => dateIndex.value >= 0 && dateIndex.value < availableDates.value.length - 1)
const hasNext = computed(() => dateIndex.value > 0)

async function fetchDates() {
  if (wasFetchedToday()) return
  try { const r = await getDates(); availableDates.value = r.data.dates || []; markFetchedToday() } catch (e) {}
}

function goPrevDay() {
  const i = dateIndex.value
  if (i >= 0 && i < availableDates.value.length - 1) { selectedDate.value = availableDates.value[i + 1]; loadData() }
}
function goNextDay() {
  const i = dateIndex.value
  if (i > 0) { selectedDate.value = availableDates.value[i - 1]; loadData() }
}

function handleSort(key) {
  if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else { sortKey.value = key; sortDir.value = 'desc' }
}

async function loadData() {
  await fetchDates()
  loading.value = true; error.value = null
  try {
    const res = await getChanTheory(selectedDate.value || undefined)
    buy1.value = res.data.buy1 || []
    buy2.value = res.data.buy2 || []
    if (!selectedDate.value && res.data.date) selectedDate.value = res.data.date
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally { loading.value = false }
}

onMounted(() => { loadData() })
</script>
