import { createI18n } from 'vue-i18n'

import { DEFAULT_LOCALE, resolveInitialLocale } from './config'
import enUS from '@/locales/en-US'
import jaJP from '@/locales/ja-JP'
import zhCN from '@/locales/zh-CN'

const messages = {
  'zh-CN': zhCN,
  'en-US': enUS,
  'ja-JP': jaJP
}

export const i18n = createI18n({
  legacy: false,
  locale: resolveInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages
})

export const setI18nLocale = (locale) => {
  i18n.global.locale.value = locale
}

export const translate = (key, params = {}) => i18n.global.t(key, params)

export default i18n

