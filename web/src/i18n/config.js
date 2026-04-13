import enUS from 'ant-design-vue/es/locale/en_US'
import jaJP from 'ant-design-vue/es/locale/ja_JP'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

export {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  SUPPORTED_LOCALES,
  getRequestLocale,
  getStoredLocale,
  localeDisplayOptions,
  normalizeLocale,
  persistLocale,
  resolveBrowserLocale,
  resolveInitialLocale
} from './localeHelpers'

export const ANTD_LOCALE_MAP = {
  'zh-CN': zhCN,
  'en-US': enUS,
  'ja-JP': jaJP
}

export const DAYJS_LOCALE_MAP = {
  'zh-CN': 'zh-cn',
  'en-US': 'en',
  'ja-JP': 'ja'
}
