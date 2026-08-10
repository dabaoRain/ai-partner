<template>
  <div class="hello-world">
    <h3>{{ msg }}</h3>
    <p>窗口尺寸：{{ width }} x {{ height }}</p>
  </div>
</template>

<script setup>
import { useWindowSize } from '@/composables/useWindowSize'

defineProps({
  msg: {
    type: String,
    default: 'Hello World',
  },
})

const { width, height } = useWindowSize()
</script>

<style scoped lang="scss">
.hello-world {
  h3 {
    margin: 0 0 8px;
    color: $primary-color;
  }

  p {
    margin: 0;
    color: $text-secondary;
  }
}
</style>
