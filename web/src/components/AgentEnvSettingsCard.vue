<template>
  <div class="agent-env-settings">
    <div class="header-section">
      <div class="header-content">
        <div class="section-title">サンドボックス環境変数</div>
        <p class="section-description">
          現在のユーザーの Agent サンドボックス環境変数を設定します。新しいサンドボックスの作成時に注入され、同名のグローバル sandbox.env を上書きします。
        </p>
      </div>
      <div class="header-actions">
        <a-button class="lucide-icon-btn" :loading="loading" @click="loadAgentEnv">
          <template #icon><RefreshCw :size="16" :class="{ spin: loading }" /></template>
          更新
        </a-button>
        <a-button type="primary" :loading="saving" @click="saveAgentEnv">
          {{ saveButtonText }}
        </a-button>
      </div>
    </div>

    <div class="env-tip">保存後は新しく作成されたサンドボックスにのみ反映され、実行中のサンドボックスには反映されません。</div>

    <a-spin :spinning="loading">
      <McpEnvEditor
        :key="editorRevision"
        :modelValue="draftEnv"
        :locked-keys="savedEnvKeys"
        conceal-locked-values
        delete-label="削除"
        add-variable-label="変数を追加"
        show-value-label="変数の値を表示"
        hide-value-label="変数の値を非表示"
        @update:modelValue="updateDraftEnv"
      />
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { RefreshCw } from 'lucide-vue-next'
import { agentEnvApi } from '@/apis/agent_env_api'
import McpEnvEditor from '@/components/McpEnvEditor.vue'

const ENV_KEY_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/
const MAX_ENV_COUNT = 200
const MAX_ENV_KEY_LENGTH = 128
const MAX_ENV_VALUE_LENGTH = 32768

const loading = ref(false)
const saving = ref(false)
const draftEnv = ref({})
const lastSavedEnv = ref({})
const editorRevision = ref(0)

const normalizeEnv = (env) => {
  if (!env || typeof env !== 'object' || Array.isArray(env)) {
    return {}
  }
  return Object.fromEntries(
    Object.entries(env)
      .map(([key, value]) => [key.trim(), value == null ? '' : String(value)])
      .filter(([key]) => key)
  )
}

const isSameEnv = (left, right) => {
  const leftEntries = Object.entries(left)
  const rightEntries = Object.entries(right)
  if (leftEntries.length !== rightEntries.length) return false
  return leftEntries.every(([key, value]) => right[key] === value)
}

const savedEnvKeys = computed(() => Object.keys(lastSavedEnv.value || {}))
const hasUnsavedChanges = computed(
  () => !isSameEnv(normalizeEnv(draftEnv.value), lastSavedEnv.value)
)
const saveButtonText = computed(() => (hasUnsavedChanges.value ? '保存（変更あり）' : '保存'))

const updateDraftEnv = (value) => {
  const nextEnv = normalizeEnv(value)
  if (!isSameEnv(draftEnv.value, nextEnv)) {
    draftEnv.value = nextEnv
  }
}

const validateEnv = (env) => {
  const entries = Object.entries(env)
  if (entries.length > MAX_ENV_COUNT) {
    message.error(`環境変数は ${MAX_ENV_COUNT} 個まで設定できます`)
    return false
  }

  for (const [key, value] of entries) {
    if (key.length > MAX_ENV_KEY_LENGTH) {
      message.error(`環境変数名は ${MAX_ENV_KEY_LENGTH} 文字以内で入力してください`)
      return false
    }
    if (!ENV_KEY_PATTERN.test(key)) {
      message.error(`環境変数名 ${key} の形式が正しくありません`)
      return false
    }
    if (value.length > MAX_ENV_VALUE_LENGTH) {
      message.error(`環境変数 ${key} の値が長すぎます`)
      return false
    }
  }
  return true
}

const loadAgentEnv = async () => {
  loading.value = true
  try {
    const res = await agentEnvApi.get()
    const env = normalizeEnv(res.env)
    draftEnv.value = env
    lastSavedEnv.value = env
    editorRevision.value += 1
  } catch (error) {
    message.error(error.message || '環境変数の読み込みに失敗しました')
  } finally {
    loading.value = false
  }
}

const saveAgentEnv = async () => {
  const env = normalizeEnv(draftEnv.value)
  if (!validateEnv(env)) return
  if (isSameEnv(env, lastSavedEnv.value)) {
    message.info('環境変数に変更はありません')
    return
  }

  saving.value = true
  try {
    await agentEnvApi.update(env)
    draftEnv.value = env
    lastSavedEnv.value = env
    editorRevision.value += 1
    message.success('環境変数を保存しました')
  } catch (error) {
    message.error(error.message || '環境変数の保存に失敗しました')
  } finally {
    saving.value = false
  }
}

onMounted(loadAgentEnv)
</script>

<style lang="less" scoped>
.agent-env-settings {
  .header-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 16px;
    margin-bottom: 12px;

    @media (max-width: 760px) {
      align-items: stretch;
      flex-direction: column;
    }
  }

  .header-content {
    flex: 1;
    min-width: 0;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .env-tip {
    margin-bottom: 14px;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--main-10);
    border: 1px solid var(--main-300);
    color: var(--main-700);
    font-size: 13px;
    line-height: 1.5;
  }
}

:deep(.spin) {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}
</style>
