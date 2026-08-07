import assert from 'node:assert/strict'
import path from 'node:path'
import { after, before, test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createServer } from 'vite'

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
let server
let buildConversationTitlePrompt

before(async () => {
  const storage = new Map()
  globalThis.localStorage = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: (key) => storage.delete(key)
  }
  globalThis.window = { localStorage: globalThis.localStorage }
  server = await createServer({ root: webRoot, server: { middlewareMode: true } })
  ;({ buildConversationTitlePrompt } = await server.ssrLoadModule('/src/utils/conversationTitle.js'))
})

after(async () => {
  await server?.close()
  delete globalThis.localStorage
  delete globalThis.window
})

test('日语请求使用日语标题提示词', () => {
  const prompt = buildConversationTitlePrompt('このサイトの内容を要約してください')

  assert.match(prompt, /あなたは会話タイトル生成器です/)
  assert.match(prompt, /30文字以内/)
  assert.doesNotMatch(prompt, /你是对话标题生成器/)
})

test('中文请求使用中文标题提示词', () => {
  const prompt = buildConversationTitlePrompt('请总结这个网站的主要内容')

  assert.match(prompt, /你是对话标题生成器/)
  assert.match(prompt, /最多 30 个字符/)
})

test('英文请求使用英文标题提示词', () => {
  const prompt = buildConversationTitlePrompt('Summarize the main points of this website')

  assert.match(prompt, /You generate conversation titles/)
  assert.match(prompt, /maximum of 30 characters/)
})

test('无法从请求判断语言时跟随界面语言', () => {
  localStorage.setItem('yuxi-locale', 'ja-JP')

  const prompt = buildConversationTitlePrompt('https://example.com')

  assert.match(prompt, /あなたは会話タイトル生成器です/)
})
