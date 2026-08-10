<template>
  <section class="chat-panel">
    <header class="chat-panel__header">
      <button
        class="chat-panel__menu"
        type="button"
        title="打开控制面板"
        @click="appStore.toggleSidebar()"
      >
        <el-icon :size="22"><Fold /></el-icon>
      </button>
      <div class="chat-panel__header-text">
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
      <!-- 豆包式输入条：左侧切换 + 中间输入/按住说话 + 右侧发送 -->
      <div
        class="chat-panel__composer"
        :class="{ 'is-voice-mode': voiceMode, 'is-listening': listening }"
      >
        <button
          class="chat-panel__mode"
          type="button"
          :disabled="sending || listening"
          :title="voiceMode ? '切换到键盘输入' : '切换到语音输入'"
          @click="toggleInputMode"
        >
          <el-icon :size="20">
            <Microphone v-if="!voiceMode" />
            <EditPen v-else />
          </el-icon>
        </button>

        <div class="chat-panel__composer-main">
          <input
            v-if="!voiceMode"
            v-model="draft"
            class="chat-panel__text"
            type="text"
            placeholder="请输入您的问题..."
            :disabled="sending"
            @keyup.enter="handleSend"
          />

          <button
            v-else
            class="chat-panel__hold"
            type="button"
            :disabled="sending || !supported"
            :title="voiceTitle"
            @contextmenu.prevent
            @pointerdown="handleVoiceStart"
            @pointerup="handleVoiceEnd"
            @pointercancel="handleVoiceEnd"
            @pointerleave="handleVoiceEnd"
          >
            {{ voiceLabel }}
          </button>
        </div>

        <button
          v-if="!voiceMode"
          class="chat-panel__send"
          type="button"
          title="发送"
          :disabled="sending || !draft.trim()"
          @click="handleSend"
        >
          <el-icon :size="20"><Promotion /></el-icon>
        </button>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  UserFilled,
  Monitor,
  Promotion,
  Microphone,
  EditPen,
  Fold,
} from '@element-plus/icons-vue'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useAppStore } from '@/store/app'

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
const appStore = useAppStore()

const draft = ref('')
const listRef = ref(null)
const voiceMode = ref(false)
const voiceStartedAt = ref(0)
const shouldSendVoice = ref(false)

const { supported, listening, start, stop, cancel } = useSpeechRecognition({
  lang: 'zh-CN',
})

const voiceLabel = computed(() => {
  if (!supported.value) return '当前浏览器不支持语音'
  if (listening.value) return '松开发送'
  return '按住 说话'
})

const voiceTitle = computed(() => {
  if (!supported.value) return '请使用 Chrome，并确保 HTTPS/localhost'
  return '按住说话，松手后发送给 AI'
})

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

function toggleInputMode() {
  if (props.sending || listening.value) return
  if (!voiceMode.value && !supported.value) {
    ElMessage.warning('当前浏览器不支持语音识别，请使用 Chrome')
    return
  }
  voiceMode.value = !voiceMode.value
}

function handleSend() {
  if (props.sending || listening.value || voiceMode.value) return
  const text = draft.value.trim()
  if (!text) return
  emit('send', text)
  draft.value = ''
}

function handleVoiceStart(event) {
  if (props.sending || !supported.value || listening.value) return
  if (event.button !== undefined && event.button !== 0) return

  event.currentTarget.setPointerCapture?.(event.pointerId)
  shouldSendVoice.value = true
  voiceStartedAt.value = Date.now()

  const ok = start({
    onFinal(text) {
      const elapsed = Date.now() - voiceStartedAt.value
      const canSend = shouldSendVoice.value && elapsed >= 500 && text
      shouldSendVoice.value = false

      if (!canSend) {
        if (elapsed < 500 && text) {
          ElMessage.info('说话时间太短，请按住再说一次')
        } else if (!text && elapsed >= 500) {
          ElMessage.info('没有识别到内容，请重试')
        }
        return
      }

      emit('send', text)
    },
    onError(message) {
      shouldSendVoice.value = false
      ElMessage.error(message)
    },
  })

  if (!ok) {
    shouldSendVoice.value = false
  }
}

function handleVoiceEnd() {
  if (!listening.value) return
  stop()
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

watch(
  () => props.sending,
  (value) => {
    if (value && listening.value) {
      shouldSendVoice.value = false
      cancel()
    }
  }
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
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  &__menu {
    display: none;
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    margin-top: 2px;
    border: none;
    border-radius: $radius-md;
    padding: 0;
    align-items: center;
    justify-content: center;
    background: $input-color;
    color: $text-color;
    cursor: pointer;

    &:active {
      opacity: 0.85;
    }
  }

  &__header-text {
    flex: 1;
    min-width: 0;
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
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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
    padding: 12px 28px calc(24px + env(safe-area-inset-bottom, 0px));
  }

  // 豆包风格单条输入框
  &__composer {
    min-height: 52px;
    padding: 6px 8px;
    border-radius: 26px;
    background: $input-color;
    border: 1px solid $border-color;
    display: flex;
    align-items: center;
    gap: 4px;
    transition:
      border-color 0.15s ease,
      background 0.15s ease,
      box-shadow 0.15s ease;

    &.is-listening {
      border-color: $primary-color;
      background: rgba(255, 90, 42, 0.12);
      box-shadow: 0 0 0 1px rgba(255, 90, 42, 0.25);
    }
  }

  &__mode {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    border: none;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: $text-secondary;
    cursor: pointer;

    &:hover:not(:disabled) {
      color: $primary-color;
      background: rgba(255, 90, 42, 0.12);
    }

    &:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
  }

  &__composer-main {
    flex: 1;
    min-width: 0;
    height: 40px;
    display: flex;
    align-items: center;
  }

  &__text {
    width: 100%;
    height: 100%;
    border: none;
    outline: none;
    background: transparent;
    color: $text-color;
    font-size: 15px;
    line-height: 40px;
    padding: 0 8px;

    &::placeholder {
      color: $text-secondary;
    }

    &:disabled {
      opacity: 0.6;
    }
  }

  &__hold {
    width: 100%;
    height: 100%;
    border: none;
    border-radius: 20px;
    background: transparent;
    color: $text-color;
    font-size: 15px;
    font-weight: 500;
    letter-spacing: 1px;
    cursor: pointer;
    user-select: none;
    touch-action: none;

    &:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
  }

  &__composer.is-listening &__hold {
    color: #fff;
  }

  &__send {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    border: none;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: $text-secondary;
    cursor: pointer;

    &:hover:not(:disabled) {
      color: $primary-color;
      background: rgba(255, 90, 42, 0.12);
    }

    &:disabled {
      opacity: 0.35;
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

@media (max-width: $breakpoint-mobile) {
  .chat-panel {
    &__header {
      padding: 12px 16px 8px;
    }

    &__menu {
      display: inline-flex;
    }

    &__title {
      font-size: 22px;
    }

    &__session {
      margin-top: 4px;
      font-size: 12px;
    }

    &__messages {
      padding: 8px 16px 12px;
      gap: 14px;
    }

    &__footer {
      padding: 8px 16px calc(12px + env(safe-area-inset-bottom, 0px));
    }

    &__bubble {
      padding: 12px 14px;
      font-size: 14px;
    }
  }
}
</style>
