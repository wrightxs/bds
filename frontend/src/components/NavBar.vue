<template>
  <nav class="bg-white shadow-sm border-b border-gray-200">
    <div class="container mx-auto px-4 max-w-7xl">
      <div class="flex items-center justify-between h-14">
        <div class="flex items-center gap-6">
          <h1 class="text-lg font-bold text-gray-800">BDS</h1>
          <div class="flex gap-1">
            <router-link
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
              :class="
                $route.path === item.path
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              "
            >
              {{ item.label }}
            </router-link>
          </div>
        </div>
        <div class="text-sm text-gray-400">
          A股每日数据统计
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
const navItems = [
  { path: '/', label: '仪表盘' },
  { path: '/top100', label: '成交额前100' },
  { path: '/limit-up', label: '涨停股票' },
]
</script>
