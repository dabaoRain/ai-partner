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
          <el-dropdown-item command="logout" class="user-menu__logout-item">
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
import { ArrowUp, SwitchButton } from '@element-plus/icons-vue'

const props = defineProps({
  username: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['logout'])

const avatarText = computed(() => {
  const name = (props.username || '?').trim()
  return name.slice(0, 1).toUpperCase()
})

function onCommand(command) {
  if (command === 'logout') {
    emit('logout')
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

  &:hover {
    background: rgba(255, 255, 255, 0.05);
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
</style>

<style lang="scss">
.user-menu-popper.el-dropdown__popper {
  background: #15171c;
  border: 1px solid #2c303a;

  .el-dropdown-menu {
    background: #15171c;
    border: none;
  }

  .el-dropdown-menu__item {
    color: #ff8b80;
    gap: 8px;

    &:hover {
      background: rgba(255, 255, 255, 0.06);
      color: #ff8b80;
    }
  }

  .el-popper__arrow::before {
    background: #15171c;
    border: 1px solid #2c303a;
  }
}
</style>
