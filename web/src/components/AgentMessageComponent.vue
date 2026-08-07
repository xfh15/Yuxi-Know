<template>
  <div v-if="message.type === 'human' && message.image_content" class="message-image">
    <img
      :src="`data:${messageImageMimeType};base64,${message.image_content}`"
      alt="用户上传的图片"
      @click="
        openImagePreview(
          `data:${messageImageMimeType};base64,${message.image_content}`,
          '用户上传的图片'
        )
      "
    />
  </div>
  <div
    class="message-box"
    :class="[
      message.type,
      customClasses,
      { 'has-attachments': message.type === 'human' && messageAttachments.length }
    ]"
  >
    <!-- 用户消息 -->
    <div
      v-if="message.type === 'human'"
      class="message-copy-btn human-copy"
      @click="copyToClipboard(message.content)"
      :class="{ 'is-copied': isCopied }"
    >
      <Check v-if="isCopied" size="14" />
      <Copy v-else size="14" />
    </div>
    <p v-if="message.type === 'human'" class="message-text">
      <MentionTextRenderer :content="message.content" :display-labels="mentionDisplayLabels" />
    </p>

    <p v-else-if="message.type === 'system'" class="message-text-system">{{ message.content }}</p>

    <!-- 助手消息 -->
    <div v-else-if="message.type === 'ai'" class="assistant-message">
      <div v-if="parsedData.reasoning_content" class="reasoning-box">
        <button
          type="button"
          class="reasoning-summary"
          :class="{ 'is-expanded': reasoningExpanded }"
          :aria-expanded="!isReasoningActive && reasoningExpanded"
          :disabled="isReasoningActive"
          @click="toggleReasoningExpanded"
        >
          <span class="summary-leading">
            <LoaderCircle v-if="isReasoningActive" size="14" class="reasoning-loading" />
            <Brain v-else size="14" />
          </span>
          <span class="summary-title">{{ isReasoningActive ? 'Thinking...' : '推理过程' }}</span>
          <span v-if="!isReasoningActive" class="summary-trailing">
            <ChevronDown v-if="reasoningExpanded" size="14" />
            <ChevronRight v-else size="14" />
          </span>
        </button>
        <div v-if="!isReasoningActive && reasoningExpanded" class="reasoning-panel">
          <p class="reasoning-content">{{ parsedData.reasoning_content }}</p>
        </div>
      </div>

      <!-- 消息内容 -->
      <MarkdownPreview
        v-if="parsedData.content"
        :key="message.id"
        :content="parsedData.content"
        code-copy
        class="message-md"
      />

      <div v-else-if="parsedData.reasoning_content" class="empty-block"></div>

      <!-- 错误提示块 -->
      <div v-if="displayError" class="error-hint">
        <span v-if="getErrorMessage">{{ getErrorMessage }}</span>
        <span v-else-if="message.error_type === 'interrupted'">回答の生成が中断されました</span>
        <span v-else-if="message.error_type === 'unexpect'">生成中にエラーが発生しました</span>
        <span v-else-if="message.error_type === 'content_guard_blocked'"
          >センシティブな内容を検出したため、出力を中断しました</span
        >
        <span v-else>{{ message.error_type || '不明なエラー' }}</span>
      </div>

      <ToolCallsGroupComponent
        v-if="!hideToolCalls && validToolCalls.length > 0"
        :tool-calls="validToolCalls"
      />

      <!-- return_direct 工具不会再触发模型回复，把工具内置的可读总结展示在工具调用之后 -->
      <MarkdownPreview
        v-if="toolDirectSummary"
        :content="toolDirectSummary"
        code-copy
        class="message-md tool-direct-summary"
      />

      <div v-if="message.isStoppedByUser" class="retry-hint">
        この回答の生成を停止しました
        <span class="retry-link" @click="emit('retryStoppedMessage', message.id)"
          >質問を再編集</span
        >
      </div>

      <div
        v-if="
          (message.role == 'received' || message.role == 'assistant') &&
          message.status == 'finished' &&
          showRefs
        "
      >
        <RefsComponent
          :message="message"
          :show-refs="showRefs"
          :is-latest-message="isLatestMessage"
          :sources="messageSources"
          @retry="emit('retry')"
          @openRefs="emit('openRefs', $event)"
        />
      </div>
      <!-- 错误消息 -->
    </div>

    <div v-if="infoStore.debugMode" class="status-info">{{ message }}</div>

    <!-- 自定义内容 -->
    <slot></slot>
  </div>

  <div
    v-if="message.type === 'human' && messageAttachments.length"
    class="human-message-attachments"
  >
    <div
      v-for="attachment in messageAttachments"
      :key="attachment.fileId"
      class="message-attachment-file"
    >
      <div class="message-attachment-icon">
        <FileTypeIcon :name="attachment.name" :size="18" />
      </div>
      <div class="message-attachment-body">
        <div class="message-attachment-name" :title="attachment.name">
          {{ attachment.name }}
        </div>
        <div class="message-attachment-meta">{{ attachment.meta }}</div>
      </div>
    </div>
  </div>

  <Teleport to="body">
    <div
      v-if="imagePreview.visible"
      class="message-image-preview-overlay"
      @click="closeImagePreview"
    >
      <button class="message-image-preview-close" title="关闭" @click.stop="closeImagePreview">
        <X :size="20" />
      </button>
      <img :src="imagePreview.src" :alt="imagePreview.alt" class="message-image-preview-img" />
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, onUnmounted } from 'vue'
import RefsComponent from '@/components/RefsComponent.vue'
import { Brain, Check, ChevronDown, ChevronRight, Copy, LoaderCircle, X } from 'lucide-vue-next'
import ToolCallsGroupComponent from '@/components/ToolCallsGroupComponent.vue'
import MarkdownPreview from '@/components/common/MarkdownPreview.vue'
import MentionTextRenderer from '@/components/common/MentionTextRenderer.vue'
import { useAgentStore } from '@/stores/agent'
import { useInfoStore } from '@/stores/info'
import { storeToRefs } from 'pinia'
import { MessageProcessor } from '@/utils/messageProcessor'
import { inferImageMimeTypeFromBase64, normalizeAttachmentPreviews } from '@/utils/file_utils'
import { buildMentionDisplayLabels } from '@/utils/mention_utils'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { enrichTaskToolCalls, parseToolCallResult } from '@/components/ToolCallingResult/toolRegistry'

const props = defineProps({
  // 消息角色：'user'|'assistant'|'sent'|'received'
  message: {
    type: Object,
    required: true
  },
  // 是否正在处理中
  isProcessing: {
    type: Boolean,
    default: false
  },
  // 自定义类
  customClasses: {
    type: Object,
    default: () => ({})
  },
  // 是否显示推理过程
  showRefs: {
    type: [Array, Boolean],
    default: () => false
  },
  // 是否为最新消息
  isLatestMessage: {
    type: Boolean,
    default: false
  },
  hideToolCalls: {
    type: Boolean,
    default: false
  },
  mention: {
    type: Object,
    default: () => null
  },
  // 是否显示调试信息 (已废弃，使用 infoStore.debugMode)
  debugMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['retry', 'retryStoppedMessage', 'openRefs'])

// 图片全屏预览
const imagePreview = ref({ visible: false, src: '', alt: '' })

const handleImagePreviewKeydown = (e) => {
  if (e.key === 'Escape') {
    closeImagePreview()
  }
}

const openImagePreview = (src, alt = '') => {
  if (!src) return
  imagePreview.value = { visible: true, src, alt }
  window.addEventListener('keydown', handleImagePreviewKeydown)
}

const closeImagePreview = () => {
  imagePreview.value = { visible: false, src: '', alt: '' }
  window.removeEventListener('keydown', handleImagePreviewKeydown)
}

onUnmounted(() => {
  window.removeEventListener('keydown', handleImagePreviewKeydown)
})

// 复制状态
const isCopied = ref(false)

const copyToClipboard = async (text) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      // 降级处理：使用传统的 execCommand 方法
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)
      if (!successful) throw new Error('execCommand failed')
    }
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy: ', err)
  }
}

// 推理面板展开状态
const reasoningExpanded = ref(false)
const isReasoningActive = computed(() => props.message.status === 'reasoning')

const toggleReasoningExpanded = () => {
  if (isReasoningActive.value) return
  reasoningExpanded.value = !reasoningExpanded.value
}

// 错误消息处理
const displayError = computed(() => {
  // 简化错误判断：只检查明确的错误类型标识
  return !!(props.message.error_type || props.message.extra_metadata?.error_type)
})

const getErrorMessage = computed(() => {
  // 优先使用直接的 error_message 字段
  if (props.message.error_message) {
    return props.message.error_message
  }

  // 其次从 extra_metadata 中获取具体的错误信息
  if (props.message.extra_metadata?.error_message) {
    return props.message.extra_metadata.error_message
  }

  // 对于已知的错误类型，返回默认提示
  switch (props.message.error_type) {
    case 'interrupted':
      return '回答の生成が中断されました'
    case 'content_guard_blocked':
      return 'センシティブな内容を検出したため、出力を中断しました'
    case 'unexpect':
      return '生成中にエラーが発生しました'
    case 'agent_error':
      return 'エージェントの取得に失敗しました'
    default:
      return null
  }
})

// 引入智能体 store
const agentStore = useAgentStore()
const { availableKnowledgeBases } = storeToRefs(agentStore)
const infoStore = useInfoStore()
const messageAttachments = computed(() =>
  normalizeAttachmentPreviews(props.message.extra_metadata?.attachments)
)
const messageImageMimeType = computed(
  () => inferImageMimeTypeFromBase64(props.message.image_content) || 'image/jpeg'
)

const mentionDisplayLabels = computed(() => buildMentionDisplayLabels(props.mention || {}))

const messageSources = computed(() => {
  if (props.message.type === 'ai') {
    return MessageProcessor.extractSourcesFromMessage(props.message, availableKnowledgeBases.value)
  }
  return { knowledgeChunks: [], webSources: [] }
})

const validToolCalls = computed(() => enrichTaskToolCalls(props.message.tool_calls))

const parsedData = computed(() => {
  const { content, reasoningContent } = MessageProcessor.parseAssistantMessageBody(props.message)
  return {
    content,
    reasoning_content: reasoningContent
  }
})

// crawl_website 等 return_direct 工具完成后，模型不再生成回复；从工具结果中取出可读总结展示在工具区外侧。
// 模型若在调工具前写了「承知しました」等正文，仍要显示总结，不能因已有 content 而隐藏。
const toolDirectSummary = computed(() => {
  for (const toolCall of validToolCalls.value) {
    const toolName = toolCall?.name || toolCall?.function?.name
    if (toolName !== 'crawl_website') continue

    const result = parseToolCallResult(toolCall)
    const summary = typeof result?.summary === 'string' ? result.summary.trim() : ''
    if (summary) return summary
  }
  return ''
})
</script>

<style lang="less" scoped>
.message-box {
  display: inline-block;
  border-radius: 1.5rem;
  margin: 0.8rem 0;
  padding: 0.625rem 1.25rem;
  user-select: text;
  word-break: break-word;
  word-wrap: break-word;
  font-size: 15px;
  line-height: 24px;
  box-sizing: border-box;
  color: var(--gray-10000);
  max-width: 100%;
  position: relative;
  letter-spacing: 0.25px;

  &.human,
  &.sent {
    max-width: 95%;
    color: var(--gray-1000);
    background-color: var(--main-50);
    align-self: flex-end;
    border-radius: 0.5rem;
    padding: 0.5rem 1rem;
  }

  &.assistant,
  &.received,
  &.ai {
    color: initial;
    width: 100%;
    text-align: left;
    margin: 0;
    padding: 0px;
    background-color: transparent;
    border-radius: 0;
  }

  .message-text {
    max-width: 100%;
    margin-bottom: 0;
    white-space: pre-line;
  }

  &.human.has-attachments,
  &.sent.has-attachments {
    margin-bottom: 0.375rem;
  }

  .message-copy-btn {
    cursor: pointer;
    color: var(--gray-400);
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    flex-shrink: 0;

    &:hover {
      color: var(--main-color);
    }

    &.is-copied {
      color: var(--color-success-500);
      opacity: 1;
    }

    &.human-copy {
      position: absolute;
      left: -28px;
      bottom: 8px;
    }
  }

  &:hover {
    .message-copy-btn {
      opacity: 1;
    }
  }

  .message-text-system {
    max-width: 100%;
    margin-bottom: 0;
    white-space: pre-line;
    color: var(--gray-600);
    font-style: italic;
    font-size: 14px;
    padding: 8px 12px;
    background-color: var(--gray-50);
    border-left: 3px solid var(--gray-300);
    border-radius: 4px;
  }

  .err-msg {
    color: var(--color-error-500);
    border: 1px solid currentColor;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    text-align: left;
    background: var(--color-error-50);
    margin-bottom: 10px;
    cursor: pointer;
  }

  .searching-msg {
    color: var(--gray-700);
    animation: colorPulse 1s infinite ease-in-out;
  }

  .reasoning-box {
    width: 100%;
    padding: 0;
    margin: 8px 0;

    .reasoning-summary {
      appearance: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      max-width: 100%;
      padding: 0;
      border: none;
      background: transparent;
      color: var(--gray-700);
      font-size: 13px;
      line-height: 20px;
      text-align: left;
      cursor: pointer;
      user-select: none;

      &:hover:not(:disabled),
      &.is-expanded {
        color: var(--gray-800);
      }

      &:disabled {
        cursor: default;
      }

      .summary-leading,
      .summary-trailing {
        display: inline-flex;
        align-items: center;
        flex-shrink: 0;
        color: var(--gray-600);
      }

      .summary-title {
        font-weight: 400;
        white-space: nowrap;
      }

      .reasoning-loading {
        animation: rotate 1s linear infinite;
      }
    }

    .reasoning-panel {
      margin-top: 4px;
      padding: 4px 0 4px 22px;
      border-top: 1px solid var(--gray-100);
    }

    .reasoning-content {
      font-size: 13px;
      color: var(--gray-800);
      white-space: pre-wrap;
      margin: 0;
      line-height: 1.6;
    }
  }

  .assistant-message {
    width: 100%;
  }

  .error-hint {
    margin: 10px 0;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    background-color: var(--color-error-50);
    color: var(--color-error-500);
    span {
      line-height: 1.5;
    }
  }

  .status-info {
    display: block;
    background-color: var(--gray-50);
    color: var(--gray-700);
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 12px;
    font-family: monospace;
    max-height: 200px;
    overflow-y: auto;
  }
}

.human-message-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: flex-end;
  align-self: flex-end;
  max-width: 95%;
  margin-bottom: 0.8rem;
}

.message-attachment-file {
  width: 220px;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--gray-200);
  border-radius: 0.625rem;
  background: var(--gray-0);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.message-attachment-icon {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 0.5rem;
  color: var(--main-color);
  background: var(--main-50);
}

.message-attachment-body {
  min-width: 0;
  flex: 1;
}

.message-attachment-name {
  overflow: hidden;
  color: var(--gray-900);
  font-size: 0.875rem;
  line-height: 1.25rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-attachment-meta {
  margin-top: 0.125rem;
  color: var(--gray-500);
  font-size: 0.75rem;
  line-height: 1rem;
}

.retry-hint {
  margin-top: 8px;
  padding: 8px 16px;
  color: var(--gray-600);
  font-size: 14px;
  text-align: left;
}

.retry-link {
  color: var(--color-info-500);
  cursor: pointer;
  margin-left: 4px;

  &:hover {
    text-decoration: underline;
  }
}

.ant-btn-icon-only {
  &:has(.anticon-stop) {
    background-color: var(--color-error-500) !important;

    &:hover {
      background-color: var(--color-error-100) !important;
    }
  }
}

@keyframes colorPulse {
  0% {
    color: var(--gray-700);
  }
  50% {
    color: var(--gray-300);
  }
  100% {
    color: var(--gray-700);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 多模态消息样式
.message-image {
  border-radius: 12px;
  overflow: hidden;
  margin-left: auto;
  /* max-height: 200px; */
  border: 1px solid rgba(255, 255, 255, 0.2);

  img {
    max-width: 100%;
    max-height: 200px;
    object-fit: contain;
    cursor: pointer;
  }
}

.message-md {
  margin: 8px 0;
}

.tool-direct-summary {
  margin-top: 12px;
}

.message-image-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.75);
  cursor: zoom-out;
}

.message-image-preview-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 4px;
  cursor: zoom-out;
}

.message-image-preview-close {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  color: var(--gray-0);
  background: rgba(255, 255, 255, 0.15);
  cursor: pointer;
  transition: background-color 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.28);
  }
}
</style>
