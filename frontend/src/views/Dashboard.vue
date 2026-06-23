<template>
  <div>
    <!-- 日期选择 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <h2 class="text-xl font-semibold text-gray-800">仪表盘</h2>
        <button
          class="px-2.5 py-1 text-xs rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap border border-blue-200"
          :disabled="isFetching"
          @click="goToday"
        >
          {{ isFetching ? '抓取中...' : '当天' }}
        </button>
        <select
          v-model="currentSource"
          class="text-xs border border-gray-200 rounded-md px-2 py-1 text-gray-500 bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-400"
          @change="switchSource"
        >
          <option value="akshare">AKShare</option>
          <option value="tushare">Tushare</option>
        </select>
      </div>
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
        <button
          v-if="currentSource === 'tushare'"
          class="px-3 py-1.5 text-sm rounded-md bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          :disabled="isFetching"
          @click="forceRefresh"
        >
          {{ isFetching ? '刷新中...' : '强制刷新' }}
        </button>
      </div>
    </div>

    <!-- 查询中提示 -->
    <div
      v-if="showQuerying && !loading && !error"
      class="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 flex items-center gap-3"
    >
      <span class="text-yellow-600 text-base">⚠</span>
      <span class="text-sm text-yellow-700 flex-1">当日数据尚未生成，系统将在交易日 18:00 自动抓取</span>
      <button
        class="px-3 py-1 text-sm rounded-md bg-yellow-500 text-white hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="isFetching"
        @click="goToday"
      >
        {{ isFetching ? '抓取中...' : '立即刷新' }}
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center py-20 text-gray-400">加载中...</div>

    <!-- 满载状态 -->
    <div v-else-if="error" class="text-center py-20 text-red-400">
      <p class="text-lg mb-2">数据加载失败</p>
      <p class="text-sm">{{ error }}</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!dashboard.date" class="text-center py-20 text-gray-400">
      <p class="text-lg mb-1">暂无数据</p>
      <p class="text-sm">系统将在每个交易日 18:00 自动抓取数据</p>
    </div>

    <template v-else>
      <!-- 三日对比 -->
      <div class="mb-8">
        <h3 class="text-sm font-medium text-gray-500 mb-3">近三日市场概览</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- 当日 -->
          <div class="bg-white rounded-lg shadow-sm border-2 border-blue-300 p-5">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">当日</span>
              <span class="text-xs text-gray-400">{{ dashboard.date }}</span>
            </div>
            <div class="space-y-3">
              <div>
                <p class="text-xs text-gray-400">成交总额</p>
                <p class="text-lg font-bold text-gray-800">{{ formatAmount(dashboard.total_turnover) }}</p>
                <p
                  v-if="dashboard.comparison && dashboard.comparison.length"
                  class="text-xs mt-0.5"
                  :class="changeClass(dashboard.total_turnover, dashboard.comparison[0].total_turnover)"
                >
                  较前日 {{ changeText(dashboard.total_turnover, dashboard.comparison[0].total_turnover) }}
                </p>
              </div>
              <div>
                <p class="text-xs text-gray-400">涨停数量</p>
                <p class="text-lg font-bold text-red-600">{{ dashboard.limit_up_count }} 只</p>
                <p
                  v-if="dashboard.comparison && dashboard.comparison.length"
                  class="text-xs mt-0.5"
                  :class="changeClass(dashboard.limit_up_count, dashboard.comparison[0].limit_up_count)"
                >
                  较前日 {{ changeText(dashboard.limit_up_count, dashboard.comparison[0].limit_up_count) }}
                </p>
              </div>
            </div>
          </div>

          <!-- 前N日 -->
          <div
            v-for="(day, idx) in dashboard.comparison"
            :key="day.date"
            class="bg-white rounded-lg shadow-sm border border-gray-200 p-5"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded">前{{ idx + 1 }}日</span>
              <span class="text-xs text-gray-400">{{ day.date }}</span>
            </div>
            <div class="space-y-3">
              <div>
                <p class="text-xs text-gray-400">成交总额</p>
                <p class="text-lg font-bold text-gray-700">{{ formatAmount(day.total_turnover) }}</p>
                <p
                  v-if="dashboard.comparison[idx + 1]"
                  class="text-xs mt-0.5"
                  :class="changeClass(day.total_turnover, dashboard.comparison[idx + 1].total_turnover)"
                >
                  较前日 {{ changeText(day.total_turnover, dashboard.comparison[idx + 1].total_turnover) }}
                </p>
              </div>
              <div>
                <p class="text-xs text-gray-400">涨停数量</p>
                <p class="text-lg font-bold text-gray-700">{{ day.limit_up_count }} 只</p>
                <p
                  v-if="dashboard.comparison[idx + 1]"
                  class="text-xs mt-0.5"
                  :class="changeClass(day.limit_up_count, dashboard.comparison[idx + 1].limit_up_count)"
                >
                  较前日 {{ changeText(day.limit_up_count, dashboard.comparison[idx + 1].limit_up_count) }}
                </p>
              </div>
            </div>
          </div>

          <!-- 无历史数据占位 -->
          <div
            v-if="!dashboard.comparison || !dashboard.comparison.length"
            class="col-span-2 bg-white rounded-lg shadow-sm border border-dashed border-gray-300 p-5 flex items-center justify-center"
          >
            <p class="text-sm text-gray-400">历史数据不足，抓取更多交易日数据后将自动显示对比</p>
          </div>
        </div>
      </div>

      <!-- 概览卡片 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">跌停数量</p>
          <p class="text-2xl font-bold text-green-600">{{ dashboard.limit_down_count ?? 0 }} 只</p>
          <p class="text-xs text-gray-400 mt-1">{{ dashboard.date }}</p>
          <p
            v-if="dashboard.comparison && dashboard.comparison.length"
            class="text-xs mt-1"
            :class="changeClass(dashboard.limit_down_count ?? 0, dashboard.comparison[0].limit_down_count ?? 0)"
          >
            较前日 {{ changeText(dashboard.limit_down_count ?? 0, dashboard.comparison[0].limit_down_count ?? 0) }}
          </p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">破板数</p>
          <p class="text-2xl font-bold text-orange-500">{{ dashboard.board_break_count ?? 0 }} 只</p>
          <p class="text-xs text-gray-400 mt-1">今日破板</p>
          <p
            v-if="dashboard.comparison && dashboard.comparison.length"
            class="text-xs mt-1"
            :class="changeClass(dashboard.board_break_count ?? 0, dashboard.comparison[0].board_break_count ?? 0)"
          >
            较前日 {{ changeText(dashboard.board_break_count ?? 0, dashboard.comparison[0].board_break_count ?? 0) }}
          </p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">破板率</p>
          <p class="text-2xl font-bold text-orange-600">{{ dashboard.board_break_rate ?? 0 }}%</p>
          <p class="text-xs text-gray-400 mt-1">触及涨停未封板比例</p>
          <p
            v-if="dashboard.comparison && dashboard.comparison.length"
            class="text-xs mt-1"
            :class="changeClass(dashboard.board_break_rate ?? 0, dashboard.comparison[0].board_break_rate ?? 0)"
          >
            较前日 {{ changeTextNum(dashboard.board_break_rate ?? 0, dashboard.comparison[0].board_break_rate ?? 0) }}
          </p>
        </div>
      </div>

      <!-- 前5预览 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- 成交额前5 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 class="font-medium text-gray-700">成交额前5</h3>
            <router-link to="/top100" class="text-sm text-blue-600 hover:text-blue-800">查看全部 →</router-link>
          </div>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-gray-500 bg-gray-50">
                <th class="px-4 py-2 text-left">排名</th>
                <th class="px-4 py-2 text-left">股票</th>
                <th class="px-4 py-2 text-right">成交额</th>
                <th class="px-4 py-2 text-right">涨跌幅</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in top5" :key="s.stock_code" class="border-b border-gray-50 hover:bg-blue-50">
                <td class="px-4 py-2 text-gray-500">{{ s.rank }}</td>
                <td class="px-4 py-2">
                  <span class="font-medium">{{ s.stock_name }}</span>
                  <span class="text-xs text-gray-400 ml-1">{{ s.stock_code }}</span>
                </td>
                <td class="px-4 py-2 text-right">{{ formatAmount(s.amount) }}</td>
                <td class="px-4 py-2 text-right" :class="pctColor(s.pct_change)">
                  {{ formatPct(s.pct_change) }}
                </td>
              </tr>
              <tr v-if="!top5.length">
                <td colspan="4" class="px-4 py-8 text-center text-gray-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 涨停前5 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 class="font-medium text-gray-700">涨停股票（按连板排序）</h3>
            <router-link to="/limit-up" class="text-sm text-blue-600 hover:text-blue-800">查看全部 →</router-link>
          </div>
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-gray-500 bg-gray-50">
                <th class="px-4 py-2 text-left">股票</th>
                <th class="px-4 py-2 text-left">板块</th>
                <th class="px-4 py-2 text-right">涨跌幅</th>
                <th class="px-4 py-2 text-center">连板</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in limitUp5" :key="s.stock_code" class="border-b border-gray-50 hover:bg-blue-50">
                <td class="px-4 py-2">
                  <span class="font-medium">{{ s.stock_name }}</span>
                  <span class="text-xs text-gray-400 ml-1">{{ s.stock_code }}</span>
                </td>
                <td class="px-4 py-2 text-gray-500 text-xs">{{ s.board_label }}</td>
                <td class="px-4 py-2 text-right text-red-600 font-medium">{{ formatPct(s.pct_change) }}</td>
                <td class="px-4 py-2 text-center">
                  <span
                    class="inline-block px-2 py-0.5 rounded text-xs font-bold"
                    :class="consecutiveBadge(s.consecutive)"
                  >
                    {{ s.consecutive }}板
                  </span>
                </td>
              </tr>
              <tr v-if="!limitUp5.length">
                <td colspan="4" class="px-4 py-8 text-center text-gray-400">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getDashboard, getTop100, getLimitUp, triggerFetch, getDataSource, setDataSource, getDates } from '../api'
import { todayStr, isQueryingToday } from '../utils/date'

const loading = ref(true)
const error = ref(null)
const selectedDate = ref('')
const dashboard = ref({})
const top5 = ref([])
const limitUp5 = ref([])
const isFetching = ref(false)
const currentSource = ref('akshare')
const availableDates = ref([])

const showQuerying = computed(() => {
  return isQueryingToday(dashboard.value.date, selectedDate.value)
})

const dateIndex = computed(() => {
  return availableDates.value.indexOf(dashboard.value.date || selectedDate.value)
})

const hasPrev = computed(() => {
  const idx = dateIndex.value
  return idx >= 0 && idx < availableDates.value.length - 1
})

const hasNext = computed(() => {
  const idx = dateIndex.value
  return idx > 0
})

async function fetchSource() {
  try {
    const res = await getDataSource()
    currentSource.value = res.data.data_source
  } catch (e) {
    // 保持默认值
  }
}

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

async function switchSource() {
  try {
    await setDataSource(currentSource.value)
  } catch (e) {
    // 切换失败回退
  }
}

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const dateParam = selectedDate.value || undefined
    const [dashRes, topRes, limitRes] = await Promise.all([
      getDashboard(dateParam),
      getTop100(dateParam),
      getLimitUp(dateParam),
    ])
    dashboard.value = dashRes.data
    top5.value = topRes.data.data.slice(0, 5)
    limitUp5.value = limitRes.data.data.slice(0, 5)
    if (!selectedDate.value && dashRes.data.date) {
      selectedDate.value = dashRes.data.date
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSource()
  fetchDates()
  loadData()
})

async function goToday() {
  const today = todayStr()
  selectedDate.value = today
  await loadData()

  // 只有当天日期确实是今天、且数据未生成时才触发抓取；已有数据则不再重复抓取
  if (dashboard.value.stock_count > 0) return

  isFetching.value = true
  error.value = null
  try {
    await triggerFetch(today)
    await loadData()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    isFetching.value = false
  }
}

async function forceRefresh() {
  const date = selectedDate.value || todayStr()
  isFetching.value = true
  error.value = null
  try {
    await triggerFetch(date, true)
    await loadData()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    isFetching.value = false
  }
}

function formatAmount(v) {
  if (v == null) return '-'
  if (v >= 1e12) return (v / 1e12).toFixed(2) + ' 万亿'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + ' 亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + ' 万'
  return v.toFixed(0)
}

function formatPct(v) {
  if (v == null) return '-'
  return (v > 0 ? '+' : '') + Number(v).toFixed(2) + '%'
}

function pctColor(v) {
  if (v == null) return ''
  return v > 0 ? 'text-red-600 font-medium' : v < 0 ? 'text-green-600 font-medium' : ''
}

function consecutiveBadge(n) {
  if (n >= 5) return 'bg-red-100 text-red-700'
  if (n >= 3) return 'bg-orange-100 text-orange-700'
  return 'bg-yellow-100 text-yellow-700'
}

function changeText(current, previous) {
  if (!previous || previous === 0) return ''
  const delta = current - previous
  const pct = ((delta / previous) * 100).toFixed(1)
  const sign = delta > 0 ? '+' : ''
  return `${sign}${pct}%`
}

function changeTextNum(current, previous) {
  if (previous == null || previous === 0) return ''
  const delta = current - previous
  const sign = delta > 0 ? '+' : ''
  return `${sign}${delta.toFixed(1)}%`
}

function changeClass(current, previous) {
  if (!previous || previous === 0) return 'text-gray-400'
  const delta = current - previous
  if (delta > 0) return 'text-red-500'
  if (delta < 0) return 'text-green-500'
  return 'text-gray-400'
}
</script>
