import { computed, ref, onMounted, onUnmounted } from 'vue'

/** 与 styles/variables.scss 中 $breakpoint-mobile 保持一致 */
export const MOBILE_BREAKPOINT = 768

/**
 * 监听窗口尺寸变化
 */
export function useWindowSize() {
  const width = ref(window.innerWidth)
  const height = ref(window.innerHeight)

  const isMobile = computed(() => width.value <= MOBILE_BREAKPOINT)

  function update() {
    width.value = window.innerWidth
    height.value = window.innerHeight
  }

  onMounted(() => {
    window.addEventListener('resize', update)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', update)
  })

  return { width, height, isMobile }
}
