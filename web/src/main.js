import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

import App from './App.vue'
import i18n from '@/i18n'
import router from './router'
import { useLocaleStore } from '@/stores/locale'
import { patchLocaleAwareNetwork } from '@/utils/localeNetwork'

import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import '@/assets/css/main.css'

const app = createApp(App)
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(Antd)

const localeStore = useLocaleStore()
localeStore.initializeLocale()
patchLocaleAwareNetwork()

// 预加载信息配置
import { useInfoStore } from '@/stores/info'
const infoStore = useInfoStore()
infoStore.loadInfoConfig()

app.mount('#app')
