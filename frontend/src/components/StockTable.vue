<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm text-left">
      <thead class="text-xs text-gray-600 uppercase bg-gray-50 border-b">
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="px-4 py-3 cursor-pointer select-none hover:bg-gray-100 transition-colors"
            :class="{ 'text-right': col.align === 'right' }"
            @click="$emit('sort', col.key)"
          >
            <div class="flex items-center gap-1" :class="{ 'justify-end': col.align === 'right' }">
              {{ col.label }}
              <span v-if="sortKey === col.key" class="text-blue-500">
                {{ sortDir === 'asc' ? '↑' : '↓' }}
              </span>
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in data"
          :key="row.stock_code || idx"
          class="border-b border-gray-100 hover:bg-blue-50 transition-colors"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            class="px-4 py-2.5"
            :class="{ 'text-right': col.align === 'right' }"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]" :index="idx">
              <span :class="getCellClass(col, row)">{{ formatValue(col, row[col.key]) }}</span>
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="!data.length" class="text-center py-16 text-gray-400">
      <p class="text-lg mb-1">暂无数据</p>
      <p class="text-sm">请选择日期查看</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  columns: { type: Array, required: true },
  data: { type: Array, default: () => [] },
  sortKey: { type: String, default: '' },
  sortDir: { type: String, default: 'desc' },
})

defineEmits(['sort'])

function formatValue(col, value) {
  if (value == null) return '-'
  if (col.format === 'amount') {
    // 成交额格式化：亿 / 万
    if (value >= 1e8) return (value / 1e8).toFixed(2) + ' 亿'
    if (value >= 1e4) return (value / 1e4).toFixed(0) + ' 万'
    return value.toFixed(0)
  }
  if (col.format === 'pct') {
    const v = Number(value)
    return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
  }
  if (col.format === 'price') {
    return Number(value).toFixed(2)
  }
  return value
}

function getCellClass(col, row) {
  if (col.key === 'pct_change' && row.pct_change != null) {
    const v = Number(row.pct_change)
    if (v > 0) return 'text-red-600 font-medium'
    if (v < 0) return 'text-green-600 font-medium'
  }
  if (col.key === 'consecutive' && row.consecutive >= 2) {
    return 'text-orange-500 font-bold'
  }
  return 'text-gray-700'
}
</script>
