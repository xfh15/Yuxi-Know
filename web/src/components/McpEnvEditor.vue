<template>
  <div class="env-editor">
    <div v-for="(row, index) in rows" :key="index" class="env-row">
      <a-input
        v-model:value="row.key"
        placeholder="Key"
        class="env-key-input"
        :disabled="isKeyLocked(row)"
      />
      <div class="env-value-field">
        <a-input
          v-model:value="row.value"
          placeholder="Value"
          class="env-value-input"
          :type="isValueHidden(row) ? 'password' : 'text'"
        />
        <a-button
          v-if="shouldConcealRow(row)"
          size="small"
          type="text"
          class="env-value-toggle"
          :aria-label="isValueHidden(row) ? props.showValueLabel : props.hideValueLabel"
          @click="toggleValueVisible(row)"
        >
          <Eye v-if="isValueHidden(row)" :size="14" />
          <EyeOff v-else :size="14" />
        </a-button>
      </div>
      <a-button size="small" type="text" danger @click="removeRow(index)">
        {{ props.deleteLabel }}
      </a-button>
    </div>
    <a-button @click="addRow" class="add-env">
      <template #icon><PlusOutlined /></template>
      {{ props.addVariableLabel }}
    </a-button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { Eye, EyeOff } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: Object,
    default: null
  },
  lockedKeys: {
    type: Array,
    default: () => []
  },
  concealLockedValues: {
    type: Boolean,
    default: false
  },
  deleteLabel: {
    type: String,
    default: '删除'
  },
  addVariableLabel: {
    type: String,
    default: '添加变量'
  },
  showValueLabel: {
    type: String,
    default: '查看变量值'
  },
  hideValueLabel: {
    type: String,
    default: '隐藏变量值'
  }
})

const emit = defineEmits(['update:modelValue'])

const rows = ref([{ key: '', value: '' }])
const syncingFromObject = ref(false)
const visibleValueKeys = ref(new Set())
const lockedKeySet = computed(() => new Set(props.lockedKeys.map((key) => String(key))))

const objectToRows = (envObj) => {
  if (!envObj || typeof envObj !== 'object') {
    return [{ key: '', value: '' }]
  }
  const entries = Object.entries(envObj)
  if (entries.length === 0) {
    return [{ key: '', value: '' }]
  }
  return entries.map(([key, value]) => ({
    key,
    value: value == null ? '' : String(value)
  }))
}

const normalizeEnvObject = (value) => {
  if (value == null) {
    return null
  }
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed
      }
    } catch {
      return null
    }
    return null
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    return value
  }
  return null
}

const rowsToObject = (rowsValue) => {
  const entries = rowsValue
    .map((row) => ({
      key: row.key.trim(),
      value: row.value
    }))
    .filter((row) => row.key)
  if (entries.length === 0) {
    return null
  }
  return Object.fromEntries(entries.map((row) => [row.key, row.value]))
}

const addRow = () => {
  rows.value.push({ key: '', value: '' })
}

const removeRow = (index) => {
  if (rows.value.length === 1) {
    rows.value[0].key = ''
    rows.value[0].value = ''
    return
  }
  rows.value.splice(index, 1)
}

const getRowKey = (row) => String(row?.key || '').trim()

const isKeyLocked = (row) => {
  const key = getRowKey(row)
  return Boolean(key && lockedKeySet.value.has(key))
}

const shouldConcealRow = (row) => props.concealLockedValues && isKeyLocked(row)

const isValueHidden = (row) => {
  const key = getRowKey(row)
  return shouldConcealRow(row) && !visibleValueKeys.value.has(key)
}

const toggleValueVisible = (row) => {
  const key = getRowKey(row)
  if (!key) return
  const next = new Set(visibleValueKeys.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  visibleValueKeys.value = next
}

watch(
  () => props.lockedKeys,
  (keys) => {
    const nextLockedKeys = new Set(keys.map((key) => String(key)))
    visibleValueKeys.value = new Set(
      [...visibleValueKeys.value].filter((key) => nextLockedKeys.has(key))
    )
  }
)

watch(
  () => props.modelValue,
  (value) => {
    const normalized = normalizeEnvObject(value)
    // コンポーネント自身が emit した値なら rows の再構築をスキップする。
    // そうしないと、key が空の行（追加直後、または key の入力中で value が空の行）が
    // rows -> object -> rows の往復同期で失われ、環境変数を追加できなくなる。
    if (JSON.stringify(normalized) === JSON.stringify(rowsToObject(rows.value))) {
      return
    }
    syncingFromObject.value = true
    if (!normalized) {
      rows.value = [{ key: '', value: '' }]
    } else {
      rows.value = objectToRows(normalized)
    }
    syncingFromObject.value = false
  },
  { immediate: true }
)

watch(
  rows,
  (value) => {
    if (syncingFromObject.value) {
      return
    }
    const obj = rowsToObject(value)
    emit('update:modelValue', obj)
  },
  { deep: true }
)
</script>

<style lang="less" scoped>
.env-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .env-row {
    display: flex;
    gap: 8px;
    align-items: center;

    .env-key-input,
    .env-value-input {
      flex: 1;
    }

    .env-value-field {
      display: flex;
      align-items: center;
      gap: 4px;
      flex: 1;
      min-width: 0;

      .env-value-input {
        min-width: 0;
      }
    }

    .env-value-toggle {
      width: 28px;
      height: 28px;
      flex: 0 0 auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--gray-500);
    }
  }

  button.add-env {
    width: fit-content;
  }
}
</style>
