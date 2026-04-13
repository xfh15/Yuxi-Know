<script setup>
import { useAgentStore } from '@/stores/agent'
import { useLocaleStore } from '@/stores/locale'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import { onMounted } from 'vue'

const agentStore = useAgentStore()
const localeStore = useLocaleStore()
const userStore = useUserStore()
const themeStore = useThemeStore()

onMounted(async () => {
  if (userStore.isLoggedIn) {
    await agentStore.initialize()
  }
})
</script>
<template>
  <a-config-provider :theme="themeStore.currentTheme" :locale="localeStore.antdLocale">
    <router-view />
  </a-config-provider>
</template>
