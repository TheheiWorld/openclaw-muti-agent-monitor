import { ref, computed } from 'vue'
import zhMessages from './zh'
import enMessages from './en'

type Messages = typeof zhMessages

const messages: Record<string, Messages> = {
  zh: zhMessages,
  en: enMessages,
}

const locale = ref<string>(localStorage.getItem('locale') || 'zh')

export function useI18n() {
  const t = (key: string): string => {
    const keys = key.split('.')
    let result: any = messages[locale.value]
    for (const k of keys) {
      if (result == null) return key
      result = result[k]
    }
    return typeof result === 'string' ? result : key
  }

  const currentLocale = computed(() => locale.value)

  const setLocale = (lang: string) => {
    locale.value = lang
    localStorage.setItem('locale', lang)
    document.documentElement.setAttribute('data-locale', lang)
  }

  // Initialize data-locale attribute
  document.documentElement.setAttribute('data-locale', locale.value)

  return { t, locale: currentLocale, setLocale }
}
