import assert from 'node:assert/strict'
import { test } from 'node:test'

import { isImeComposing } from '../../src/utils/keyboard.js'

test('识别输入法组合期间的键盘事件', () => {
  assert.equal(isImeComposing({ isComposing: true, keyCode: 13 }), true)
  assert.equal(isImeComposing({ isComposing: false, keyCode: 229 }), true)
})

test('普通 Enter 不会被识别为输入法组合事件', () => {
  assert.equal(isImeComposing({ isComposing: false, keyCode: 13 }), false)
})
