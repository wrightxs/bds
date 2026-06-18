<template>
  <div class="flex flex-wrap gap-2">
    <button
      v-for="opt in options"
      :key="opt.value"
      @click="$emit('select', opt.value)"
      class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
      :class="
        modelValue === opt.value
          ? 'bg-blue-100 text-blue-700 shadow-sm'
          : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
      "
    >
      {{ opt.label }}
      <span v-if="opt.count != null" class="ml-1 text-xs text-gray-400">({{ opt.count }})</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, required: true },
})

defineEmits(['select'])
</script>
