<template>
  <div class="language-switcher" :class="[`language-switcher--${variant}`]">
    <button
      v-for="item in localeDisplayOptions"
      :key="item.value"
      type="button"
      class="switcher-option"
      :class="{ active: localeStore.currentLanguage === item.value }"
      @click="localeStore.setLocale(item.value)"
    >
      <span class="switcher-short">{{ item.shortLabel }}</span>
      <span v-if="showLabel" class="switcher-label">{{ item.nativeLabel }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { localeDisplayOptions } from '@/i18n/config'
import { useLocaleStore } from '@/stores/locale'

const props = defineProps({
  variant: {
    type: String,
    default: 'default'
  }
})

const localeStore = useLocaleStore()
const showLabel = computed(() => !['compact', 'sidebar'].includes(props.variant))
</script>

<style scoped lang="less">
.language-switcher {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border: 1px solid var(--gray-150);
  border-radius: 999px;
  background: var(--gray-0);
}

.switcher-option {
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 999px;
  padding: 6px 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;

  &:hover {
    background: var(--gray-25);
    color: var(--color-text);
  }

  &.active {
    background: var(--main-50);
    color: var(--main-color);
  }
}

.switcher-short {
  font-size: 12px;
  font-weight: 600;
}

.switcher-label {
  font-size: 12px;
}

.language-switcher--compact {
  padding: 2px;

  .switcher-option {
    padding: 4px 8px;
  }
}

.language-switcher--sidebar {
  width: 100%;
  flex-direction: column;
  gap: 4px;
  padding: 0;
  border: none;
  background: transparent;

  .switcher-option {
    width: 100%;
    justify-content: center;
    padding: 6px 0;
    border-radius: 10px;
    background: var(--gray-0);
    border: 1px solid var(--gray-100);
  }

  .switcher-short {
    font-size: 11px;
    letter-spacing: 0.02em;
  }
}
</style>
