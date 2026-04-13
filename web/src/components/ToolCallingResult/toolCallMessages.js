const interpolate = (template, params = {}) =>
  String(template).replace(/\{(\w+)\}/g, (_, key) => {
    const value = params[key]
    return value === undefined || value === null ? '' : String(value)
  })

const resolveMessage = (messages, key) =>
  key.split('.').reduce((value, segment) => value?.[segment], messages)

export const createTranslator = (messages) => (key, params = {}) => {
  const message = resolveMessage(messages, key)
  if (typeof message !== 'string') return key
  return interpolate(message, params)
}

export const getToolCallLabel = (toolCall) => {
  const rawName = toolCall?.name || toolCall?.function?.name || ''
  const normalized = typeof rawName === 'string' ? rawName.replaceAll('_', ' ') : 'tool'
  return normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : 'Tool'
}

export const buildToolCallsSummaryTitle = ({ t, toolCalls }) => {
  if (toolCalls.length === 1) {
    return t('toolCalls.summary.single', { tool: getToolCallLabel(toolCalls[0]) })
  }

  return t('toolCalls.summary.multiple', { count: toolCalls.length })
}

export const buildToolCallsNamesMeta = (toolCalls) => {
  const names = toolCalls.map(getToolCallLabel).filter(Boolean)
  const uniqueNames = [...new Set(names)]
  const visibleNames = uniqueNames.slice(0, 3)

  if (!visibleNames.length) return ''

  return `${visibleNames.join(' · ')}${
    uniqueNames.length > visibleNames.length ? ` +${uniqueNames.length - visibleNames.length}` : ''
  }`
}

export const buildToolCallsStatusSummary = ({ t, toolCalls }) => {
  const successCount = toolCalls.filter(
    (toolCall) => toolCall.status === 'success' || toolCall.tool_call_result
  ).length
  const runningCount = toolCalls.filter(
    (toolCall) =>
      toolCall.status !== 'success' && toolCall.status !== 'error' && !toolCall.tool_call_result
  ).length
  const errorCount = toolCalls.filter((toolCall) => toolCall.status === 'error').length

  if (successCount > 0 && successCount === toolCalls.length) {
    return t('toolCalls.status.completed')
  }

  const parts = []
  if (errorCount > 0) parts.push(t('toolCalls.status.failedCount', { count: errorCount }))
  if (runningCount > 0) parts.push(t('toolCalls.status.runningCount', { count: runningCount }))

  return parts.join(' · ')
}

export const buildBaseToolHeaderText = ({ t, toolName, status }) => {
  const key =
    status === 'error'
      ? 'toolCalls.base.error'
      : status === 'success'
        ? 'toolCalls.base.success'
        : 'toolCalls.base.running'

  return t(key, { tool: toolName })
}
