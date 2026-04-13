import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { setI18nLocale } from '@/i18n'
import {
  ANTD_LOCALE_MAP,
  DAYJS_LOCALE_MAP,
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  normalizeLocale,
  persistLocale,
  resolveInitialLocale
} from '@/i18n/config'
import { setDayjsLocale } from '@/utils/time'

const applyDocumentLanguage = (locale) => {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
  }
}

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref(resolveInitialLocale())

  const antdLocale = computed(() => ANTD_LOCALE_MAP[locale.value] || ANTD_LOCALE_MAP[DEFAULT_LOCALE])
  const dayjsLocale = computed(() => DAYJS_LOCALE_MAP[locale.value] || DAYJS_LOCALE_MAP[DEFAULT_LOCALE])
  const currentLanguage = computed(() => locale.value)

  const setLocale = (nextLocale) => {
    const normalized = normalizeLocale(nextLocale)
    locale.value = normalized
    persistLocale(normalized)
    setI18nLocale(normalized)
    setDayjsLocale(normalized)
    applyDocumentLanguage(normalized)
  }

  const initializeLocale = () => {
    setLocale(resolveInitialLocale())
  }

  return {
    locale,
    currentLanguage,
    supportedLocales: SUPPORTED_LOCALES,
    antdLocale,
    dayjsLocale,
    setLocale,
    resolveInitialLocale,
    initializeLocale
  }
})

