<template>
  <aside class="chat-sidebar">
    <h2 class="chat-sidebar__title">AI控制面板</h2>

    <button class="chat-sidebar__new-btn" type="button" @click="$emit('create')">
      <el-icon :size="16"><EditPen /></el-icon>
      <span>新建会话</span>
    </button>

    <div class="chat-sidebar__section chat-sidebar__section--history">
      <div class="chat-sidebar__label">历史会话</div>
      <ul class="chat-sidebar__history">
        <li
          v-for="item in sessions"
          :key="item.id"
          class="chat-sidebar__history-item"
          :class="{ 'is-active': item.id === activeId }"
          @click="$emit('select', item.id)"
        >
          <el-icon class="chat-sidebar__history-icon" :size="16">
            <Document />
          </el-icon>
          <span class="chat-sidebar__history-name">{{ item.id }}</span>
          <button
            class="chat-sidebar__delete"
            type="button"
            title="删除会话"
            @click.stop="$emit('remove', item.id)"
          >
            <el-icon :size="14"><CloseBold /></el-icon>
          </button>
        </li>
      </ul>
    </div>

    <div class="chat-sidebar__section">
      <div class="chat-sidebar__label">名字</div>
      <el-input
        :model-value="name"
        placeholder="请输入名字"
        @update:model-value="$emit('update:name', $event)"
      />
    </div>

    <div class="chat-sidebar__section chat-sidebar__section--grow">
      <div class="chat-sidebar__label">性格</div>
      <el-input
        :model-value="personality"
        type="textarea"
        :rows="4"
        resize="none"
        placeholder="请输入性格设定"
        @update:model-value="$emit('update:personality', $event)"
      />
    </div>

    <!-- 登录用户：左下角头像与菜单；游客仅显示提示 -->
    <UserMenu
      v-if="isLoggedIn"
      :username="username"
      @logout="$emit('logout')"
    />
    <div v-else class="chat-sidebar__guest-bar">
      <span>游客模式</span>
      <button type="button" @click="$emit('open-auth')">登录账号</button>
    </div>
  </aside>
</template>

<script setup>
import { EditPen, Document, CloseBold } from '@element-plus/icons-vue'
import UserMenu from '@/components/chat/UserMenu.vue'

defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
  activeId: {
    type: String,
    default: '',
  },
  name: {
    type: String,
    default: '',
  },
  personality: {
    type: String,
    default: '',
  },
  isLoggedIn: {
    type: Boolean,
    default: false,
  },
  username: {
    type: String,
    default: '',
  },
})

defineEmits([
  'create',
  'select',
  'remove',
  'update:name',
  'update:personality',
  'open-auth',
  'logout',
])
</script>

<style scoped lang="scss">
.chat-sidebar {
  width: $sidebar-width;
  flex-shrink: 0;
  height: 100%;
  padding: 20px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: $sidebar-color;
  border-right: 1px solid $border-color;
  overflow: auto;

  &__title {
    margin: 0;
    font-size: 22px;
    font-weight: 700;
    color: $text-color;
    letter-spacing: 0.5px;
  }

  &__new-btn {
    width: 100%;
    height: 42px;
    border: none;
    border-radius: $radius-md;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: #fff;
    font-size: 15px;
    cursor: pointer;
    background: linear-gradient(90deg, #ff4d1a 0%, #ff7a3d 100%);
    transition: opacity 0.2s ease, transform 0.15s ease;

    &:hover {
      opacity: 0.92;
    }

    &:active {
      transform: scale(0.98);
    }
  }

  &__section {
    display: flex;
    flex-direction: column;
    gap: 8px;

    &--grow {
      flex: 1;
      min-height: 0;
    }
  }

  &__label {
    font-size: 14px;
    color: $text-secondary;
  }

  &__history {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 220px;
    overflow: auto;
  }

  &__history-item {
    height: 40px;
    padding: 0 10px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    gap: 8px;
    background: $input-color;
    cursor: pointer;
    transition: background 0.15s ease;

    &:hover {
      background: #2a2e38;
    }

    &.is-active {
      background: $primary-color;
      color: #fff;

      .chat-sidebar__delete {
        color: #fff;
      }
    }
  }

  &__history-icon {
    flex-shrink: 0;
    opacity: 0.9;
  }

  &__history-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;
  }

  &__delete {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    border: none;
    border-radius: 4px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: $danger-color;
    cursor: pointer;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
    }
  }

  &__guest-bar {
    flex-shrink: 0;
    margin-top: auto;
    padding-top: 12px;
    border-top: 1px solid $border-color;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    font-size: 13px;
    color: $text-secondary;

    button {
      border: none;
      background: transparent;
      color: $primary-soft;
      cursor: pointer;
      font-size: 13px;
      padding: 0;

      &:hover {
        color: #fff;
      }
    }
  }
}

@media (max-width: $breakpoint-mobile) {
  .chat-sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 20;
    width: min(#{$sidebar-width}, 85vw);
    transform: translateX(-100%);
    transition: transform 0.2s ease;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.35);

    &.is-open {
      transform: translateX(0);
    }

    &__section--history {
      flex: 1;
      min-height: 0;
    }

    &__history {
      flex: 1;
      min-height: 0;
      max-height: none;
    }
  }
}
</style>
