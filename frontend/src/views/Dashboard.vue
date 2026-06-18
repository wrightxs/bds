<template>
  <div>
    <!-- 日期选择 -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold text-gray-800">仪表盘</h2>
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
      <!-- 概览卡片 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">市场总成交额</p>
          <p class="text-2xl font-bold text-gray-800">{{ formatAmount(dashboard.total_turnover) }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ dashboard.date }}</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">涨停股票数</p>
          <p class="text-2xl font-bold text-red-600">{{ dashboard.limit_up_count }}</p>
          <p class="text-xs text-gray-400 mt-1">今日涨停</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm text-gray-500 mb-1">成交额榜首</p>
          <p v-if="dashboard.top_stock" class="text-xl font-bold text-gray-800">
            {{ dashboard.top_stock.stock_name }}
            <span class="text-sm text-gray-400 font-normal">{{ dashboard.top_stock.stock_code }}</span>
          </p>
          <p v-if="dashboard.top_stock" class="text-sm mt-1">
            成交额 {{ formatAmount(dashboard.top_stock.amount) }}
          </p>
          <p v-else class="text-sm text-gray-400">-</p>
          <p class="text-xs text-gray-400 mt-1">按成交额排名</p>
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
import { ref, onMounted, watch } from 'vue'
import { getDashboard, getTop100, getLimitUp } from '../api'

const loading = ref(true)
const error = ref(null)
const selectedDate = ref('')
const dashboard = ref({})
const top5 = ref([])
const limitUp5 = ref([])

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

onMounted(loadData)

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
</script>
