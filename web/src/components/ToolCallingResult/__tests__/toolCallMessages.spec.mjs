import assert from 'node:assert/strict'

import jaJP from '../../../locales/ja-JP.js'
import {
  buildBaseToolHeaderText,
  buildToolCallsStatusSummary,
  buildToolCallsSummaryTitle,
  createTranslator
} from '../toolCallMessages.js'

const t = createTranslator(jaJP)

assert.equal(
  buildToolCallsSummaryTitle({
    t,
    toolCalls: Array.from({ length: 24 }, (_, index) => ({
      name: index % 2 === 0 ? 'read_file' : 'list_kbs'
    }))
  }),
  '24個のツールを呼び出しました'
)

assert.equal(
  buildToolCallsSummaryTitle({
    t,
    toolCalls: [{ name: 'read_file' }]
  }),
  '使用ツール: Read file'
)

assert.equal(
  buildToolCallsStatusSummary({
    t,
    toolCalls: [
      { status: 'success' },
      { status: 'success', tool_call_result: { content: 'ok' } }
    ]
  }),
  '完了'
)

assert.equal(
  buildToolCallsStatusSummary({
    t,
    toolCalls: [
      { status: 'error' },
      { status: 'running' },
      { status: 'running' }
    ]
  }),
  '1件失敗 · 2件実行中'
)

assert.equal(
  buildBaseToolHeaderText({
    t,
    toolName: 'Read file',
    status: 'running'
  }),
  'ツールを呼び出し中: Read file'
)

assert.equal(
  buildBaseToolHeaderText({
    t,
    toolName: 'Read file',
    status: 'error'
  }),
  'ツール Read file の実行に失敗しました'
)

console.log('toolCallMessages: all assertions passed')
