import MessageProcessor from './messageProcessor.js'
import { enrichTaskToolCalls } from '../components/ToolCallingResult/toolRegistry.js'

const hasVisibleAssistantBody = (message) => {
  if (!message || message.type !== 'ai') return true

  const { content, reasoningContent } = MessageProcessor.parseAssistantMessageBody(message)
  return Boolean(
    content ||
    reasoningContent ||
    message.error_type ||
    message.extra_metadata?.error_type ||
    message.isStoppedByUser
  )
}

const defaultEnrichToolCalls = (message) => enrichTaskToolCalls(message?.tool_calls)

const parseToolResultPayload = (toolCall) => {
  const content = toolCall?.tool_call_result?.content ?? toolCall?.result
  if (!content) return null
  if (typeof content === 'object') return content
  if (typeof content !== 'string') return null
  try {
    return JSON.parse(content)
  } catch {
    return null
  }
}

/** 从 return_direct 工具结果中提取应展示在工具区外侧的可读总结。 */
export const extractPostToolSummary = (toolCalls = []) => {
  for (const toolCall of toolCalls) {
    const toolName = toolCall?.name || toolCall?.function?.name
    if (toolName !== 'crawl_website') continue
    const result = parseToolResultPayload(toolCall)
    const summary = typeof result?.summary === 'string' ? result.summary.trim() : ''
    if (summary) return summary
  }
  return ''
}

// 将 AI 消息拆成“正文块”和“工具块”，再跨消息合并相邻工具块。
// crawl_website 等 return_direct 工具的总结挂在 tool-group 后展示，因为聊天 UI 用 hide-tool-calls 拆分了消息与工具。
export const getConversationDisplayItems = (
  conv,
  { enrichToolCalls = defaultEnrichToolCalls } = {}
) => {
  if (!Array.isArray(conv?.messages) || conv.messages.length === 0) return []

  const items = []
  let pendingToolGroup = null

  const flushToolGroup = () => {
    if (pendingToolGroup && pendingToolGroup.toolCalls.length > 0) {
      const summary = extractPostToolSummary(pendingToolGroup.toolCalls)
      items.push({
        ...pendingToolGroup,
        ...(summary ? { postToolSummary: summary } : {})
      })
    }
    pendingToolGroup = null
  }

  conv.messages.forEach((message, index) => {
    if (message.type !== 'ai') {
      flushToolGroup()
      items.push({
        type: 'message',
        key: message.id || `message-${index}`,
        message,
        sourceIndex: index
      })
      return
    }

    if (hasVisibleAssistantBody(message)) {
      flushToolGroup()
      items.push({
        type: 'message',
        key: message.id || `message-${index}`,
        message,
        sourceIndex: index
      })
    }

    const toolCalls = enrichToolCalls(message)
    if (toolCalls.length === 0) return

    if (!pendingToolGroup) {
      pendingToolGroup = {
        type: 'tool-group',
        key: `tool-group-${message.id || index}`,
        toolCalls: []
      }
    }
    pendingToolGroup.toolCalls.push(...toolCalls)
  })

  flushToolGroup()
  return items
}
