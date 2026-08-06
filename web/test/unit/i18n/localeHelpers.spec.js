import assert from 'node:assert/strict'

import {
  DEFAULT_LOCALE,
  normalizeLocale,
  resolveBrowserLocale
} from '../../../src/i18n/localeHelpers.js'

const originalNavigator = globalThis.navigator

Object.defineProperty(globalThis, 'navigator', {
  configurable: true,
  value: {
    languages: ['ja-JP', 'en-US']
  }
})

assert.equal(normalizeLocale('en'), 'en-US')
assert.equal(normalizeLocale('ja_JP'), 'ja-JP')
assert.equal(normalizeLocale('zh-Hans'), 'zh-CN')
assert.equal(normalizeLocale('fr-FR'), DEFAULT_LOCALE)
assert.equal(resolveBrowserLocale(), 'ja-JP')

if (originalNavigator === undefined) {
  delete globalThis.navigator
} else {
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: originalNavigator
  })
}

console.log('localeHelpers: all assertions passed')
