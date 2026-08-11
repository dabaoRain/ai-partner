<template>
  <div class="auth-gate">
    <div class="auth-gate__glow auth-gate__glow--a" />
    <div class="auth-gate__glow auth-gate__glow--b" />

    <div class="auth-gate__card">
      <div class="auth-gate__brand">
        <div class="auth-gate__logo">AI</div>
        <h1 class="auth-gate__title">AI 智能伴侣</h1>
        <p class="auth-gate__subtitle">登录后跨端同步会话；也可先以游客体验</p>
      </div>

      <div class="auth-gate__tabs">
        <button
          type="button"
          class="auth-gate__tab"
          :class="{ 'is-active': mode === 'login' }"
          @click="mode = 'login'"
        >
          登录
        </button>
        <button
          type="button"
          class="auth-gate__tab"
          :class="{ 'is-active': mode === 'register' }"
          @click="mode = 'register'"
        >
          注册
        </button>
      </div>

      <form class="auth-gate__form" @submit.prevent="submit">
        <label class="auth-gate__field">
          <span>用户名</span>
          <el-input
            v-model="username"
            size="large"
            autocomplete="username"
            placeholder="字母数字下划线，3-32 位"
          />
        </label>
        <label class="auth-gate__field">
          <span>密码</span>
          <el-input
            v-model="password"
            type="password"
            size="large"
            show-password
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            placeholder="至少 8 位"
          />
        </label>

        <label v-if="mode === 'register'" class="auth-gate__consent">
          <el-checkbox v-model="privacyAccepted" />
          <span>
            我已阅读并同意
            <button type="button" class="auth-gate__link" @click.stop.prevent="showPolicy = true">
              《隐私说明》
            </button>
            （收集目的、会话数据与注销权利）
          </span>
        </label>

        <p v-else class="auth-gate__hint">
          继续即表示了解我们会处理账号与会话数据，详见
          <button type="button" class="auth-gate__link" @click="showPolicy = true">隐私说明</button>
        </p>

        <el-button
          class="auth-gate__submit"
          type="primary"
          size="large"
          native-type="submit"
          :loading="loading"
        >
          {{ mode === 'login' ? '进入聊天' : '注册并进入' }}
        </el-button>
      </form>

      <div class="auth-gate__divider">
        <span>或者</span>
      </div>

      <button
        type="button"
        class="auth-gate__guest"
        :disabled="guestLoading"
        @click="enterAsGuest"
      >
        {{ guestLoading ? '正在进入…' : '游客登录，先体验一下' }}
      </button>
      <p class="auth-gate__guest-hint">
        游客模式仅在本机保存会话归属；可随时登录并明确授权后合并。
      </p>
    </div>

    <el-dialog v-model="showPolicy" title="隐私说明" width="480px" append-to-body>
      <div v-if="policy" class="auth-gate__policy">
        <p v-for="(item, idx) in policy.collection_purposes" :key="idx">{{ item }}</p>
        <h4>保留策略</h4>
        <p v-for="(val, key) in policy.retention" :key="key">{{ key }}：{{ val }}</p>
      </div>
      <el-skeleton v-else animated :rows="4" />
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { login, register } from '@/api/auth'
import { ensureAuthReady } from '@/utils/authBootstrap'
import { fetchPrivacyPolicy } from '@/api/privacy'

const emit = defineEmits(['success', 'guest'])

const mode = ref('login')
const username = ref('')
const password = ref('')
const loading = ref(false)
const guestLoading = ref(false)
const privacyAccepted = ref(false)
const showPolicy = ref(false)
const policy = ref(null)

onMounted(async () => {
  try {
    policy.value = await fetchPrivacyPolicy()
  } catch (error) {
    console.error(error)
  }
})

async function submit() {
  const name = username.value.trim()
  const pwd = password.value
  if (name.length < 3) {
    ElMessage.warning('用户名至少 3 位')
    return
  }
  if (pwd.length < 8) {
    ElMessage.warning('密码至少 8 位')
    return
  }
  if (mode.value === 'register' && !privacyAccepted.value) {
    ElMessage.warning('请先阅读并同意隐私说明')
    return
  }
  loading.value = true
  try {
    const api = mode.value === 'login' ? login : register
    const body =
      mode.value === 'register'
        ? { username: name, password: pwd, privacy_accepted: true }
        : { username: name, password: pwd }
    const res = await api(body)
    emit('success', res)
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function enterAsGuest() {
  guestLoading.value = true
  try {
    await ensureAuthReady()
    emit('guest')
  } catch (error) {
    console.error(error)
    ElMessage.error('游客进入失败，请稍后重试')
  } finally {
    guestLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.auth-gate {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(255, 90, 42, 0.22), transparent 55%),
    radial-gradient(900px 500px at 90% 110%, rgba(80, 120, 255, 0.12), transparent 50%),
    $bg-color;
}

.auth-gate__glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;

  &--a {
    width: 280px;
    height: 280px;
    left: 12%;
    top: 18%;
    background: rgba(255, 90, 42, 0.18);
    animation: float-a 8s ease-in-out infinite;
  }

  &--b {
    width: 220px;
    height: 220px;
    right: 14%;
    bottom: 16%;
    background: rgba(100, 140, 255, 0.12);
    animation: float-b 10s ease-in-out infinite;
  }
}

.auth-gate__card {
  position: relative;
  z-index: 1;
  width: min(420px, calc(100vw - 32px));
  padding: 36px 32px 28px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(160deg, rgba(32, 35, 44, 0.96), rgba(18, 20, 26, 0.98));
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(12px);
}

.auth-gate__brand {
  text-align: center;
  margin-bottom: 28px;
}

.auth-gate__logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #ff4d1a 0%, #ff8a4a 100%);
  box-shadow: 0 10px 24px rgba(255, 77, 26, 0.35);
}

.auth-gate__title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  color: $text-color;
  letter-spacing: 0.5px;
}

.auth-gate__subtitle {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: $text-secondary;
}

.auth-gate__tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px;
  margin-bottom: 20px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.28);
}

.auth-gate__tab {
  height: 38px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: $text-secondary;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;

  &.is-active {
    color: #fff;
    background: linear-gradient(90deg, #ff4d1a 0%, #ff7a3d 100%);
  }
}

.auth-gate__form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.auth-gate__field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: $text-secondary;

  :deep(.el-input__wrapper) {
    background: $input-color;
    box-shadow: none;
    border: 1px solid $border-color;
  }

  :deep(.el-input__wrapper:hover),
  :deep(.el-input__wrapper.is-focus) {
    border-color: rgba(255, 90, 42, 0.55);
  }
}

.auth-gate__submit {
  width: 100%;
  margin-top: 6px;
  height: 44px;
  border: none;
  font-weight: 600;
  background: linear-gradient(90deg, #ff4d1a 0%, #ff7a3d 100%);
}

.auth-gate__divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0 14px;
  color: $text-secondary;
  font-size: 12px;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: $border-color;
  }
}

.auth-gate__guest {
  width: 100%;
  height: 42px;
  border-radius: 10px;
  border: 1px solid $border-color;
  background: transparent;
  color: $text-color;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;

  &:hover:not(:disabled) {
    border-color: rgba(255, 255, 255, 0.28);
    background: rgba(255, 255, 255, 0.04);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.auth-gate__consent {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: $text-secondary;
}

.auth-gate__hint,
.auth-gate__guest-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: $text-secondary;
}

.auth-gate__guest-hint {
  margin-top: 10px;
  text-align: center;
}

.auth-gate__link {
  border: none;
  padding: 0;
  background: transparent;
  color: $primary-soft;
  cursor: pointer;
  font-size: inherit;

  &:hover {
    text-decoration: underline;
  }
}

.auth-gate__policy {
  color: $text-color;
  font-size: 13px;
  line-height: 1.6;
  max-height: 360px;
  overflow: auto;

  h4 {
    margin: 12px 0 6px;
    color: $text-secondary;
  }

  p {
    margin: 0 0 8px;
  }
}

@keyframes float-a {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(18px);
  }
}

@keyframes float-b {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-16px);
  }
}
</style>
