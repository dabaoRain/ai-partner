<template>
  <section class="chat-panel">
    <header class="chat-panel__header">
      <div>
        <h1 class="chat-panel__title">AI智能伴侣</h1>
        <p class="chat-panel__session">当前会话: {{ sessionId || '暂无会话' }}</p>
      </div>
    </header>

    <div ref="listRef" class="chat-panel__messages">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="chat-panel__row"
        :class="`is-${msg.role}`"
      >
        <div class="chat-panel__avatar" :class="`is-${msg.role}`">
          <el-icon :size="18">
            <UserFilled v-if="msg.role === 'user'" />
            <Monitor v-else />
          </el-icon>
        </div>
        <div
          class="chat-panel__bubble"
          :class="{ 'is-thinking': isThinking(msg, index) }"
        >
          <div v-if="isThinking(msg, index)" class="chat-panel__thinking">
            <span class="chat-panel__thinking-text">思考中</span>
            <span class="chat-panel__dots" aria-hidden="true">
              <i /><i /><i />
            </span>
          </div>
          <template v-else>{{ msg.content }}</template>
        </div>
      </div>
    </div>

    <footer class="chat-panel__footer">
      <div class="chat-panel__input-wrap">
        <el-input
          v-model="draft"
          class="chat-panel__input"
          placeholder="请输入您的问题..."
          :disabled="sending"
          @keyup.enter="handleSend"
        />
        <button
          class="chat-panel__send"
          type="button"
          title="发送"
          :disabled="sending"
          @click="handleSend"
        >
          <el-icon :size="20"><Promotion /></el-icon>
        </button>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { UserFilled, Monitor, Promotion } from '@element-plus/icons-vue'

const props = defineProps({
  sessionId: {
    type: String,
    default: '',
  },
  messages: {
    type: Array,
    default: () => [],
  },
  sending: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['send'])

const draft = ref('')
const listRef = ref(null)

/** 空气泡且正在等待流式首包时展示 thinking */
function isThinking(msg, index) {
  return (
    props.sending &&
    msg.role === 'assistant' &&
    !msg.content &&
    index === props.messages.length - 1
  )
}

async function scrollToBottom() {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

function handleSend() {
  if (props.sending) return
  const text = draft.value.trim()
  if (!text) return
  emit('send', text)
  draft.value = ''
}

watch(
  () => [
    props.messages.length,
    props.messages.map((item) => item.content).join(''),
  ],
  () => {
    scrollToBottom()
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.chat-panel {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: $bg-color;

  &__header {
    padding: 28px 28px 12px;
  }

  &__title {
    margin: 0;
    font-size: 34px;
    font-weight: 700;
    color: $text-color;
    line-height: 1.2;
  }

  &__session {
    margin: 8px 0 0;
    font-size: 14px;
    color: $text-secondary;
  }

  &__messages {
    flex: 1;
    min-height: 0;
    padding: 8px 28px 16px;
    overflow: auto;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  &__row {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  &__avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #fff;

    &.is-user {
      background: #e53935;
    }

    &.is-assistant {
      background: $primary-color;
    }
  }

  &__bubble {
    width: 100%;
    padding: 14px 16px;
    border-radius: $radius-lg;
    background: $bubble-color;
    color: $text-color;
    font-size: 15px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;

    &.is-thinking {
      min-height: 48px;
      display: flex;
      align-items: center;
    }
  }

  &__thinking {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: $text-secondary;
  }

  &__thinking-text {
    font-size: 14px;
  }

  &__dots {
    display: inline-flex;
    align-items: center;
    gap: 4px;

    i {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: $primary-color;
      opacity: 0.35;
      animation: chat-thinking-bounce 1.2s infinite ease-in-out;

      &:nth-child(2) {
        animation-delay: 0.15s;
      }

      &:nth-child(3) {
        animation-delay: 0.3s;
      }
    }
  }

  &__footer {
    padding: 12px 28px 24px;
  }

  &__input-wrap {
    position: relative;
  }

  &__input {
    :deep(.el-input__wrapper) {
      min-height: 48px;
      padding-right: 48px;
      border-radius: $radius-md;
      background: $input-color !important;
    }
  }

  &__send {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    width: 34px;
    height: 34px;
    border: none;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: $text-secondary;
    cursor: pointer;

    &:hover {
      color: $primary-color;
      background: rgba(255, 90, 42, 0.12);
    }

    &:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
  }
}

@keyframes chat-thinking-bounce {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.35;
  }

  40% {
    transform: translateY(-4px);
    opacity: 1;
  }
}
</style>
