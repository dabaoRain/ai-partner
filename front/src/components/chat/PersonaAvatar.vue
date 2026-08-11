<template>
  <el-image
    v-if="resolved"
    :src="resolved"
    :preview-src-list="clickable ? [resolved] : []"
    :initial-index="0"
    :preview-teleported="true"
    fit="cover"
    :class="['persona-avatar', customClass]"
    :alt="alt"
    hide-on-click-modal
    @click.stop
  />
  <span v-else :class="['persona-avatar', 'persona-avatar--empty', customClass]">
    <slot />
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { resolvePersonaAvatar } from '@/constants/personaPresets'

const props = defineProps({
  /** 原始 avatar_url（如 /static/personas/1.jpg） */
  url: {
    type: String,
    default: '',
  },
  alt: {
    type: String,
    default: '',
  },
  /** 是否点击放大预览 */
  clickable: {
    type: Boolean,
    default: true,
  },
  customClass: {
    type: String,
    default: '',
  },
})

const resolved = computed(() => resolvePersonaAvatar(props.url))
</script>

<style scoped lang="scss">
.persona-avatar {
  display: block;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);

  :deep(.el-image__inner) {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  :deep(.el-image__wrapper),
  :deep(.el-image__placeholder),
  :deep(.el-image__error) {
    width: 100%;
    height: 100%;
  }

  &--empty {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
}

/* 可预览时显示手型 */
.persona-avatar:deep(.el-image__inner) {
  cursor: zoom-in;
}
</style>
