import { getRequestLocale } from '@/i18n/config'

const FETCH_PATCH_FLAG = '__yuxiLocaleFetchPatched__'
const XHR_PATCH_FLAG = '__yuxiLocaleXhrPatched__'

const isApiRequest = (url) => {
  if (!url || typeof window === 'undefined') {
    return false
  }

  try {
    const parsed = new URL(url, window.location.origin)
    return parsed.origin === window.location.origin && parsed.pathname.startsWith('/api')
  } catch {
    return false
  }
}

const withLocaleHeader = (headers) => {
  const nextHeaders = new Headers(headers || {})
  if (!nextHeaders.has('X-Yuxi-Locale')) {
    nextHeaders.set('X-Yuxi-Locale', getRequestLocale())
  }
  return nextHeaders
}

export const patchLocaleAwareNetwork = () => {
  if (typeof window === 'undefined') {
    return
  }

  if (!window[FETCH_PATCH_FLAG]) {
    const originalFetch = window.fetch.bind(window)

    window.fetch = (input, init = {}) => {
      const targetUrl = typeof input === 'string' ? input : input?.url
      if (!isApiRequest(targetUrl)) {
        return originalFetch(input, init)
      }

      if (input instanceof Request) {
        const request = new Request(input, {
          ...init,
          headers: withLocaleHeader(init.headers || input.headers)
        })
        return originalFetch(request)
      }

      return originalFetch(input, {
        ...init,
        headers: withLocaleHeader(init.headers)
      })
    }

    window[FETCH_PATCH_FLAG] = true
  }

  if (!window[XHR_PATCH_FLAG]) {
    const originalOpen = XMLHttpRequest.prototype.open
    const originalSend = XMLHttpRequest.prototype.send

    XMLHttpRequest.prototype.open = function open(method, url, ...rest) {
      this.__yuxiLocaleTarget = url
      return originalOpen.call(this, method, url, ...rest)
    }

    XMLHttpRequest.prototype.send = function send(body) {
      if (isApiRequest(this.__yuxiLocaleTarget)) {
        this.setRequestHeader('X-Yuxi-Locale', getRequestLocale())
      }
      return originalSend.call(this, body)
    }

    window[XHR_PATCH_FLAG] = true
  }
}

