import { defineStore } from 'pinia'
import { ref } from 'vue'
import { MOBILE_BREAKPOINT } from '@/composables/useWindowSize'

export const useAppStore = defineStore('app', () => {
  const title = ref(import.meta.env.VITE_APP_TITLE || 'AI智能伴侣')
  // 窄屏默认收起侧栏
  const sidebarCollapsed = ref(
    typeof window !== 'undefined' && window.innerWidth <= MOBILE_BREAKPOINT,
  )

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function openSidebar() {
    sidebarCollapsed.value = false
  }

  function closeSidebar() {
    sidebarCollapsed.value = true
  }

  return {
    title,
    sidebarCollapsed,
    toggleSidebar,
    openSidebar,
    closeSidebar,
  }
})
