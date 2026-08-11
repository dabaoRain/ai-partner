<template>
  <aside class="chat-sidebar">
    <h2 class="chat-sidebar__title">AI智能伴侣</h2>

    <div class="chat-sidebar__section chat-sidebar__section--history">
      <div class="chat-sidebar__label">我的伴侣</div>
      <ul class="chat-sidebar__history">
        <li
          v-for="item in sessions"
          :key="item.id"
          class="chat-sidebar__history-item"
          :class="{ 'is-active': item.id === activeId }"
          @click="$emit('select', item.id)"
        >
          <el-icon v-if="!item.avatarUrl" class="chat-sidebar__history-icon" :size="16">
            <Document />
          </el-icon>
          <PersonaAvatar
            v-if="item.avatarUrl"
            class="chat-sidebar__history-avatar"
            :url="item.avatarUrl"
            :alt="item.name || '伴侣'"
          />
          <div class="chat-sidebar__history-main">
            <span class="chat-sidebar__history-name" :title="item.title || item.name || item.id">
              {{ item.title || item.name || item.id }}
            </span>
            <span class="chat-sidebar__history-meta" :title="sessionMeta(item)">
              {{ sessionMeta(item) }}
            </span>
          </div>
          <el-dropdown
            trigger="click"
            placement="bottom-end"
            popper-class="chat-sidebar-action-menu"
            @command="(command) => $emit('session-action', { id: item.id, command })"
            @click.stop
          >
            <button
              class="chat-sidebar__more"
              type="button"
              title="更多操作"
              @click.stop
            >
              <el-icon :size="16"><MoreFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="reset">清空并重开</el-dropdown-item>
                <el-dropdown-item command="clear" class="is-danger" divided>
                  清空聊天记录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </li>
      </ul>
      <p v-if="!sessions.length" class="chat-sidebar__empty-hint">
        {{ partnerName ? '在主区开始你们的第一句话' : '请先选择一位伴侣' }}
      </p>
    </div>

    <button
      class="chat-sidebar__persona-entry"
      type="button"
      @click="$emit('open-persona')"
    >
      <div class="chat-sidebar__persona-avatar" aria-hidden="true">
        <el-icon :size="20"><User /></el-icon>
      </div>
      <div class="chat-sidebar__persona-entry-main">
        <div class="chat-sidebar__persona-entry-title">伴侣库</div>
        <div class="chat-sidebar__persona-entry-summary" :title="personaSummary">
          {{ personaSummary }}
        </div>
      </div>
      <el-icon :size="16"><ArrowRight /></el-icon>
    </button>

    <!-- 登录用户：左下角头像与菜单；游客仅显示提示 -->
    <UserMenu
      v-if="isLoggedIn"
      :username="username"
      @logout="$emit('logout')"
      @open-privacy="$emit('open-privacy')"
    />
    <div v-else class="chat-sidebar__guest-bar">
      <span>游客模式</span>
      <button type="button" @click="$emit('open-auth')">登录账号</button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { Document, ArrowRight, User, MoreFilled } from '@element-plus/icons-vue'
import UserMenu from '@/components/chat/UserMenu.vue'
import PersonaAvatar from '@/components/chat/PersonaAvatar.vue'

const props = defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
  activeId: {
    type: String,
    default: '',
  },
  partnerName: {
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
  'select',
  'session-action',
  'open-persona',
  'open-auth',
  'logout',
  'open-privacy',
])

const personaSummary = computed(() => {
  return props.partnerName ? '查看或更换官方伴侣' : '挑选一位官方伴侣'
})

function sessionMeta(item) {
  return item.region || '官方伴侣'
}
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

  &__section {
    display: flex;
    flex-direction: column;
    gap: 8px;

    &--history {
      flex: 1;
      min-height: 0;
    }
  }

  &__label {
    font-size: 14px;
    color: $text-secondary;
  }

  &__empty-hint {
    margin: 4px 0 0;
    padding: 0 2px;
    font-size: 12px;
    line-height: 1.5;
    color: $text-secondary;
  }

  &__history {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: none;
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  &__history-item {
    min-height: 54px;
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

      .chat-sidebar__history-meta {
        color: rgba(255, 255, 255, 0.82);
      }

      .chat-sidebar__more {
        color: #fff;
      }
    }
  }

  &__history-icon {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    opacity: 0.9;
  }

  &__history-avatar {
    width: 34px;
    height: 42px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  &__history-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  &__history-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;
    font-weight: 600;
  }

  &__history-meta {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 11px;
    line-height: 1.35;
    color: $text-secondary;
  }

  &__more {
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    border: none;
    border-radius: 6px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: $text-secondary;
    cursor: pointer;

    &:hover,
    &:focus-visible {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
      outline: none;
    }

    &:active {
      transform: scale(0.96);
    }
  }

  &__persona-entry {
    flex-shrink: 0;
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px;
    border: 1px solid $border-color;
    border-radius: $radius-md;
    background: $input-color;
    color: $text-color;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s ease, border-color 0.15s ease;

    &:hover {
      background: #2a2e38;
      border-color: #3a404c;
    }
  }

  &__persona-avatar {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 90, 42, 0.14);
    color: $primary-soft;
  }

  &__persona-entry-main {
    flex: 1;
    min-width: 0;
  }

  &__persona-entry-title {
    font-size: 14px;
    font-weight: 600;
  }

  &__persona-entry-summary {
    margin-top: 4px;
    font-size: 12px;
    color: $text-secondary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

:global(.chat-sidebar-action-menu.el-popper) {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: #20242c;
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.38);
  overflow: hidden;
}

:global(.chat-sidebar-action-menu .el-popper__arrow::before) {
  border-color: rgba(255, 255, 255, 0.08);
  background: #20242c;
}

:global(.chat-sidebar-action-menu .el-dropdown-menu) {
  min-width: 148px;
  padding: 6px;
  border: none;
  background: transparent;
}

:global(.chat-sidebar-action-menu .el-dropdown-menu__item) {
  height: 36px;
  border-radius: 7px;
  padding: 0 12px;
  color: #e8edf4;
  font-size: 13px;
  line-height: 36px;
}

:global(.chat-sidebar-action-menu .el-dropdown-menu__item:not(.is-disabled):focus),
:global(.chat-sidebar-action-menu .el-dropdown-menu__item:not(.is-disabled):hover) {
  background: rgba(255, 90, 42, 0.13);
  color: #fff;
}

:global(.chat-sidebar-action-menu .el-dropdown-menu__item--divided) {
  margin-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

:global(.chat-sidebar-action-menu .el-dropdown-menu__item.is-danger) {
  color: #ff8d7a;
}

:global(.chat-sidebar-action-menu .el-dropdown-menu__item.is-danger:not(.is-disabled):focus),
:global(.chat-sidebar-action-menu .el-dropdown-menu__item.is-danger:not(.is-disabled):hover) {
  background: rgba(255, 77, 26, 0.15);
  color: #ffb09f;
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
  }
}
</style>
