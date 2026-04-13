export const DEFAULT_LOCALE = 'zh-CN'
export const LOCALE_STORAGE_KEY = 'yuxi-locale'
export const SUPPORTED_LOCALES = ['zh-CN', 'en-US', 'ja-JP']

const LOCALE_ALIAS_MAP = {
  zh: 'zh-CN',
  'zh-cn': 'zh-CN',
  'zh-hans': 'zh-CN',
  en: 'en-US',
  'en-us': 'en-US',
  ja: 'ja-JP',
  'ja-jp': 'ja-JP'
}

export const localeDisplayOptions = [
  { value: 'zh-CN', shortLabel: '中', nativeLabel: '简体中文' },
  { value: 'en-US', shortLabel: 'EN', nativeLabel: 'English' },
  { value: 'ja-JP', shortLabel: '日', nativeLabel: '日本語' }
]

const normalizeToken = (value) => {
  if (!value) {
    return ''
  }

  return String(value).trim().toLowerCase().replace(/_/g, '-')
}

export const normalizeLocale = (value) => {
  const normalized = normalizeToken(value)
  if (!normalized) {
    return DEFAULT_LOCALE
  }

  if (LOCALE_ALIAS_MAP[normalized]) {
    return LOCALE_ALIAS_MAP[normalized]
  }

  const base = normalized.split('-')[0]
  return LOCALE_ALIAS_MAP[base] || DEFAULT_LOCALE
}

export const getStoredLocale = () => {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null
  }

  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY)
  return stored ? normalizeLocale(stored) : null
}

export const resolveBrowserLocale = () => {
  if (typeof navigator === 'undefined') {
    return DEFAULT_LOCALE
  }

  const candidates = Array.isArray(navigator.languages)
    ? navigator.languages
    : [navigator.language].filter(Boolean)

  for (const candidate of candidates) {
    const locale = normalizeLocale(candidate)
    if (SUPPORTED_LOCALES.includes(locale)) {
      return locale
    }
  }

  return DEFAULT_LOCALE
}

export const resolveInitialLocale = () => getStoredLocale() || resolveBrowserLocale()

export const persistLocale = (locale) => {
  if (typeof window === 'undefined' || !window.localStorage) {
    return
  }

  window.localStorage.setItem(LOCALE_STORAGE_KEY, normalizeLocale(locale))
}

export const getRequestLocale = () => resolveInitialLocale()

