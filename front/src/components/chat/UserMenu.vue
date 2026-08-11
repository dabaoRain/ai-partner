<template>
  <div class="user-menu">
    <el-dropdown
      trigger="click"
      placement="top-start"
      popper-class="user-menu-popper"
      @command="onCommand"
    >
      <button type="button" class="user-menu__trigger">
        <div class="user-menu__avatar" aria-hidden="true">{{ avatarText }}</div>
        <div class="user-menu__meta">
          <div class="user-menu__name" :title="username">{{ username }}</div>
          <div class="user-menu__hint">已登录</div>
        </div>
        <el-icon class="user-menu__caret" :size="14"><ArrowUp /></el-icon>
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="privacy">
            <el-icon :size="16"><Setting /></el-icon>
            <span>隐私与账号</span>
          </el-dropdown-item>
          <el-dropdown-item command="logout" class="user-menu__logout-item" divided>
            <el-icon :size="16"><SwitchButton /></el-icon>
            <span>退出登录</span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowUp, SwitchButton, Setting } from '@element-plus/icons-vue'

const props = defineProps({
  username: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['logout', 'open-privacy'])

const avatarText = computed(() => {
  const name = (props.username || '?').trim()
  return name.slice(0, 1).toUpperCase()
})

function onCommand(command) {
  if (command === 'logout') {
    emit('logout')
  } else if (command === 'privacy') {
    emit('open-privacy')
  }
}
</script>

<style scoped lang="scss">
.user-menu {
  flex-shrink: 0;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid $border-color;
}

.user-menu__trigger {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border: none;
  border-radius: $radius-md;
  background: transparent;
  color: $text-color;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;

  &:hover,
  &:focus,
  &:focus-visible {
    outline: none;
    background: rgba(255, 255, 255, 0.06);
  }
}

.user-menu__avatar {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #ff4d1a 0%, #ff8a4a 100%);
}

.user-menu__meta {
  flex: 1;
  min-width: 0;
}

.user-menu__name {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-menu__hint {
  margin-top: 2px;
  font-size: 12px;
  color: $text-secondary;
}

.user-menu__caret {
  color: $text-secondary;
  flex-shrink: 0;
}

:deep(.el-dropdown) {
  width: 100%;
  display: block;
}

:deep(.el-tooltip__trigger:focus-visible) {
  outline: none;
}
</style>

<style lang="scss">
/* 覆盖 Element Plus 下拉默认浅色 hover/focus，保持侧栏暗色风格 */
.user-menu-popper.el-dropdown__popper,
.user-menu-popper.el-popper {
  --el-bg-color-overlay: #15171c;
  --el-border-color-light: #2c303a;
  --el-dropdown-menuItem-hover-fill: rgba(255, 255, 255, 0.08);
  --el-dropdown-menuItem-hover-color: #f8fafc;
  --el-text-color-regular: #f3f4f6;
  background: #15171c !important;
  border: 1px solid #2c303a !important;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45);

  .el-dropdown-menu {
    background: #15171c !important;
    border: none !important;
    padding: 6px;
  }

  .el-dropdown-menu__item {
    color: #f3f4f6 !important;
    gap: 8px;
    border-radius: 8px;
    margin: 0;

    &:hover,
    &:focus,
    &:focus-visible,
    &:not(.is-disabled):hover,
    &:not(.is-disabled):focus {
      background-color: rgba(255, 255, 255, 0.08) !important;
      color: #fff !important;
    }
  }

  .user-menu__logout-item {
    color: #ff8b80 !important;

    &:hover,
    &:focus,
    &:not(.is-disabled):hover,
    &:not(.is-disabled):focus {
      background-color: rgba(255, 80, 80, 0.12) !important;
      color: #ffb4ab !important;
    }
  }

  .el-popper__arrow::before {
    background: #15171c !important;
    border: 1px solid #2c303a !important;
  }
}
</style>
