import assert from 'node:assert/strict'
import test from 'node:test'

// 仅测总结解析逻辑，避免引入依赖 lucide 的 toolRegistry。
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

const extractPostToolSummary = (toolCalls = []) => {
  for (const toolCall of toolCalls) {
    const toolName = toolCall?.name || toolCall?.function?.name
    if (toolName !== 'crawl_website') continue
    const result = parseToolResultPayload(toolCall)
    const summary = typeof result?.summary === 'string' ? result.summary.trim() : ''
    if (summary) return summary
  }
  return ''
}

test('crawl_website 工具结果中的 summary 可被解析为外侧正文', () => {
  const summary = extractPostToolSummary([
    {
      name: 'crawl_website',
      tool_call_result: {
        content: JSON.stringify({
          pages: 3,
          pdfs: 1,
          qa: 10,
          summary: 'サイト資料の収集が完了しました。\n\n- ページ：3 件'
        })
      }
    }
  ])
  assert.match(summary, /ページ：3 件/)
})

test('非 crawl_website 或无 summary 时不展示总结', () => {
  assert.equal(extractPostToolSummary([{ name: 'web_search', tool_call_result: { content: '{}' } }]), '')
  assert.equal(
    extractPostToolSummary([
      { name: 'crawl_website', tool_call_result: { content: JSON.stringify({ pages: 1 }) } }
    ]),
    ''
  )
})
