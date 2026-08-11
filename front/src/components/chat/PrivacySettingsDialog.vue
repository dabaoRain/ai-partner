<template>
  <el-dialog
    :model-value="modelValue"
    width="640px"
    align-center
    destroy-on-close
    class="privacy-dialog"
    :show-close="true"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="privacy-hero">
        <div class="privacy-hero__badge" aria-hidden="true">
          <el-icon :size="20"><Lock /></el-icon>
        </div>
        <div class="privacy-hero__text">
          <h2 class="privacy-hero__title">隐私与账号</h2>
          <p class="privacy-hero__desc">管理数据用途、偏好、质量概览与账号注销</p>
        </div>
      </div>
    </template>

    <div class="privacy-nav" role="tablist">
      <button
        v-for="item in tabs"
        :key="item.id"
        type="button"
        class="privacy-nav__item"
        :class="{ 'is-active': tab === item.id }"
        role="tab"
        :aria-selected="tab === item.id"
        @click="tab = item.id"
      >
        <el-icon :size="16"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </button>
    </div>

    <div class="privacy-body">
      <!-- 收集说明 -->
      <section v-show="tab === 'policy'" class="privacy-pane">
        <template v-if="policy">
          <div class="privacy-card privacy-card--intro">
            <div class="privacy-card__kicker">Privacy Policy</div>
            <h3 class="privacy-card__title">{{ policy.title }}</h3>
            <p class="privacy-card__meta">
              版本 {{ policy.version }} · 更新于 {{ policy.updated_at }}
            </p>
          </div>

          <div class="privacy-section">
            <div class="privacy-section__head">
              <el-icon :size="16"><Document /></el-icon>
              <span>收集目的</span>
            </div>
            <ul class="privacy-list">
              <li v-for="(item, idx) in policy.collection_purposes" :key="idx">
                <span class="privacy-list__index">{{ idx + 1 }}</span>
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>

          <div class="privacy-section">
            <div class="privacy-section__head">
              <el-icon :size="16"><Timer /></el-icon>
              <span>数据保留</span>
            </div>
            <div class="privacy-retain">
              <div
                v-for="(val, key) in policy.retention"
                :key="key"
                class="privacy-retain__item"
              >
                <div class="privacy-retain__label">{{ retentionLabel(key) }}</div>
                <div class="privacy-retain__value">{{ val }}</div>
              </div>
            </div>
          </div>

          <div class="privacy-section">
            <div class="privacy-section__head">
              <el-icon :size="16"><User /></el-icon>
              <span>你可控制</span>
            </div>
            <ul class="privacy-chips">
              <li v-for="(item, idx) in policy.user_controls" :key="idx">{{ item }}</li>
            </ul>
          </div>
        </template>
        <el-skeleton v-else animated :rows="8" />
      </section>

      <!-- 偏好 -->
      <section v-show="tab === 'prefs'" class="privacy-pane">
        <div class="privacy-pref">
          <div class="privacy-pref__icon" aria-hidden="true">
            <el-icon :size="22"><Memo /></el-icon>
          </div>
          <div class="privacy-pref__content">
            <div class="privacy-pref__title">长期记忆</div>
            <div class="privacy-pref__tag">预留能力</div>
            <p class="privacy-pref__desc">
              当前版本不会写入长期记忆。打开开关仅保存你的偏好，供后续记忆功能启用时沿用。
            </p>
          </div>
          <el-switch
            v-model="memoryEnabled"
            size="large"
            :loading="prefLoading"
            inline-prompt
            active-text="开"
            inactive-text="关"
            @change="onMemoryChange"
          />
        </div>
        <div class="privacy-note">
          <el-icon :size="14"><InfoFilled /></el-icon>
          <span>关闭记忆不会影响当前会话历史；删除会话或注销账号仍可清除数据。</span>
        </div>
      </section>

      <!-- 质量看板 -->
      <section v-show="tab === 'board'" class="privacy-pane">
        <template v-if="summary">
          <div class="privacy-board-banner">
            <div>
              <div class="privacy-board-banner__title">近 {{ summary.days }} 天质量概览</div>
              <p class="privacy-board-banner__hint">{{ summary.retention_hint }}</p>
            </div>
          </div>

          <div class="privacy-section__head privacy-section__head--spaced">
            <el-icon :size="16"><DataLine /></el-icon>
            <span>全局事件</span>
          </div>
          <div class="privacy-stats">
            <div
              v-for="item in boardTotals"
              :key="item.key"
              class="privacy-stat"
            >
              <div class="privacy-stat__val">{{ item.value }}</div>
              <div class="privacy-stat__key">{{ item.label }}</div>
            </div>
          </div>

          <div class="privacy-section__head privacy-section__head--spaced">
            <el-icon :size="16"><UserFilled /></el-icon>
            <span>我的数据</span>
          </div>
          <div class="privacy-stats">
            <div
              v-for="item in boardMine"
              :key="'m-' + item.key"
              class="privacy-stat privacy-stat--mine"
            >
              <div class="privacy-stat__val">{{ item.value }}</div>
              <div class="privacy-stat__key">{{ item.label }}</div>
            </div>
          </div>
        </template>
        <el-skeleton v-else animated :rows="6" />
      </section>

      <!-- 注销 -->
      <section v-show="tab === 'delete'" class="privacy-pane">
        <div class="privacy-danger">
          <div class="privacy-danger__head">
            <div class="privacy-danger__icon">
              <el-icon :size="20"><WarningFilled /></el-icon>
            </div>
            <div>
              <div class="privacy-danger__title">注销账号</div>
              <p class="privacy-danger__desc">
                将永久删除你的会话、消息、偏好与相关日志，且不可恢复。
              </p>
            </div>
          </div>
          <ul class="privacy-danger__list">
            <li>历史对话与人设配置将被清除</li>
            <li>登录凭证立即失效</li>
            <li>此操作无法撤销</li>
          </ul>
          <label class="privacy-danger__field">
            <span>输入当前密码确认</span>
            <el-input
              v-model="deletePassword"
              type="password"
              size="large"
              show-password
              placeholder="请输入密码"
            />
          </label>
          <el-button
            type="danger"
            size="large"
            class="privacy-danger__btn"
            :loading="deleting"
            :disabled="!deletePassword"
            @click="onDeleteAccount"
          >
            确认注销账号
          </el-button>
        </div>
      </section>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Lock,
  Document,
  Timer,
  User,
  Memo,
  InfoFilled,
  DataLine,
  UserFilled,
  WarningFilled,
  Setting,
  PieChart,
  Delete,
} from '@element-plus/icons-vue'
import {
  deleteAccount,
  fetchPreferences,
  fetchPrivacyPolicy,
  updatePreferences,
} from '@/api/privacy'
import { fetchAnalyticsSummary } from '@/api/analytics'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const tabs = [
  { id: 'policy', label: '收集说明', icon: Document },
  { id: 'prefs', label: '偏好', icon: Setting },
  { id: 'board', label: '质量看板', icon: PieChart },
  { id: 'delete', label: '注销', icon: Delete },
]

const EVENT_LABELS = {
  user_registered: '注册',
  user_login: '登录',
  first_chat: '首聊',
  chat_message: '发消息',
  chat_completed: '完成回复',
  chat_failed: '失败',
  chat_cancelled: '停止生成',
  feedback: '反馈',
  session_deleted: '删会话',
  account_deleted: '注销',
  app_open: '打开应用',
  session_created: '建立关系线',
  guest_claimed: '合并匿名',
}

const RETENTION_LABELS = {
  account: '账号数据',
  guest: '游客数据',
  chat_request_logs: '请求日志',
  analytics: '质量统计',
}

const tab = ref('policy')
const policy = ref(null)
const memoryEnabled = ref(false)
const prefLoading = ref(false)
const summary = ref(null)
const deletePassword = ref('')
const deleting = ref(false)

function retentionLabel(key) {
  return RETENTION_LABELS[key] || key
}

function mapStats(totals) {
  const entries = Object.entries(totals || {})
  // 优先展示核心事件，数字大的靠前
  return entries
    .map(([key, value]) => ({
      key,
      value,
      label: EVENT_LABELS[key] || key,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
}

const boardTotals = computed(() => mapStats(summary.value?.totals))
const boardMine = computed(() => mapStats(summary.value?.my_totals))

async function loadAll() {
  policy.value = null
  summary.value = null
  deletePassword.value = ''
  try {
    const [p, pref, board] = await Promise.all([
      fetchPrivacyPolicy(),
      fetchPreferences(),
      fetchAnalyticsSummary(7),
    ])
    policy.value = p
    memoryEnabled.value = Boolean(pref?.memory_enabled)
    summary.value = board
  } catch (error) {
    console.error(error)
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      tab.value = 'policy'
      loadAll()
    }
  },
)

async function onMemoryChange(val) {
  prefLoading.value = true
  try {
    await updatePreferences({ memory_enabled: Boolean(val) })
    ElMessage.success(val ? '已开启记忆预留开关' : '已关闭记忆预留开关')
  } catch (error) {
    memoryEnabled.value = !val
    console.error(error)
  } finally {
    prefLoading.value = false
  }
}

async function onDeleteAccount() {
  try {
    await ElMessageBox.confirm(
      '确定注销并删除全部个人对话数据吗？此操作不可撤销。',
      '注销确认',
      { type: 'warning', confirmButtonText: '确认注销', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await deleteAccount(deletePassword.value)
    ElMessage.success('账号已注销')
    emit('update:modelValue', false)
    emit('deleted')
  } catch (error) {
    console.error(error)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped lang="scss">
.privacy-hero {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-right: 28px;

  &__badge {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    color: #fff;
    background: linear-gradient(135deg, #ff4d1a 0%, #ff8a4a 100%);
    box-shadow: 0 10px 24px rgba(255, 77, 26, 0.28);
    flex-shrink: 0;
  }

  &__title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: $text-color;
    letter-spacing: 0.3px;
  }

  &__desc {
    margin: 4px 0 0;
    font-size: 12px;
    color: $text-secondary;
  }
}

.privacy-nav {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  padding: 4px;
  margin-bottom: 16px;
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.28);

  &__item {
    height: 40px;
    border: none;
    border-radius: 10px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    background: transparent;
    color: $text-secondary;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;

    &.is-active {
      color: #fff;
      background: linear-gradient(90deg, #ff4d1a 0%, #ff7a3d 100%);
      box-shadow: 0 8px 18px rgba(255, 77, 26, 0.25);
    }

    &:hover:not(.is-active) {
      color: $text-color;
      background: rgba(255, 255, 255, 0.04);
    }
  }
}

.privacy-body {
  max-height: min(58vh, 520px);
  overflow: auto;
  padding-right: 2px;
}

.privacy-pane {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.privacy-card {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: linear-gradient(145deg, rgba(40, 44, 54, 0.9), rgba(24, 26, 32, 0.95));

  &__kicker {
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: $primary-soft;
    margin-bottom: 6px;
  }

  &__title {
    margin: 0;
    font-size: 17px;
    font-weight: 700;
  }

  &__meta {
    margin: 6px 0 0;
    font-size: 12px;
    color: $text-secondary;
  }
}

.privacy-section {
  &__head {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-size: 13px;
    font-weight: 600;
    color: $text-color;

    &--spaced {
      margin-top: 4px;
    }

    .el-icon {
      color: $primary-soft;
    }
  }
}

.privacy-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;

  li {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 12px;
    background: $input-color;
    border: 1px solid rgba(255, 255, 255, 0.04);
    font-size: 13px;
    line-height: 1.55;
    color: $text-color;
  }

  &__index {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-size: 11px;
    font-weight: 700;
    color: #fff;
    background: rgba(255, 90, 42, 0.85);
  }
}

.privacy-retain {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;

  &__item {
    padding: 12px 14px;
    border-radius: 12px;
    background: $input-color;
    border: 1px solid rgba(255, 255, 255, 0.04);
  }

  &__label {
    font-size: 12px;
    font-weight: 600;
    color: $primary-soft;
    margin-bottom: 6px;
  }

  &__value {
    font-size: 12px;
    line-height: 1.5;
    color: $text-secondary;
  }
}

.privacy-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;

  li {
    padding: 8px 12px;
    border-radius: 999px;
    font-size: 12px;
    color: $text-color;
    background: rgba(255, 90, 42, 0.12);
    border: 1px solid rgba(255, 90, 42, 0.22);
  }
}

.privacy-pref {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px;
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(40, 44, 54, 0.95), rgba(22, 24, 30, 0.98));
  border: 1px solid rgba(255, 255, 255, 0.06);

  &__icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    color: $primary-soft;
    background: rgba(255, 90, 42, 0.12);
    flex-shrink: 0;
  }

  &__content {
    flex: 1;
    min-width: 0;
  }

  &__title {
    font-size: 15px;
    font-weight: 700;
  }

  &__tag {
    display: inline-block;
    margin-top: 6px;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    color: $primary-soft;
    background: rgba(255, 90, 42, 0.12);
  }

  &__desc {
    margin: 10px 0 0;
    font-size: 12px;
    line-height: 1.6;
    color: $text-secondary;
  }
}

.privacy-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed $border-color;
  color: $text-secondary;
  font-size: 12px;
  line-height: 1.5;

  .el-icon {
    margin-top: 2px;
    color: $primary-soft;
  }
}

.privacy-board-banner {
  padding: 16px 18px;
  border-radius: 16px;
  background:
    radial-gradient(500px 120px at 0% 0%, rgba(255, 90, 42, 0.18), transparent 55%),
    $input-color;
  border: 1px solid rgba(255, 255, 255, 0.05);

  &__title {
    font-size: 15px;
    font-weight: 700;
  }

  &__hint {
    margin: 8px 0 0;
    font-size: 12px;
    line-height: 1.5;
    color: $text-secondary;
  }
}

.privacy-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.privacy-stat {
  padding: 14px 12px;
  border-radius: 14px;
  background: $input-color;
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: transform 0.15s ease, border-color 0.15s ease;

  &:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 90, 42, 0.35);
  }

  &--mine {
    background: rgba(255, 90, 42, 0.08);
  }

  &__val {
    font-size: 22px;
    font-weight: 760;
    letter-spacing: 0.3px;
  }

  &__key {
    margin-top: 6px;
    font-size: 12px;
    color: $text-secondary;
  }
}

.privacy-danger {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(231, 76, 60, 0.35);
  background:
    radial-gradient(420px 160px at 100% 0%, rgba(231, 76, 60, 0.16), transparent 60%),
    rgba(34, 20, 20, 0.75);

  &__head {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  &__icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    color: #ff8b80;
    background: rgba(231, 76, 60, 0.16);
    flex-shrink: 0;
  }

  &__title {
    font-size: 16px;
    font-weight: 700;
    color: #ffb4ac;
  }

  &__desc {
    margin: 6px 0 0;
    font-size: 12px;
    line-height: 1.55;
    color: $text-secondary;
  }

  &__list {
    margin: 14px 0;
    padding-left: 18px;
    color: $text-secondary;
    font-size: 12px;
    line-height: 1.7;
  }

  &__field {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 12px;
    color: $text-secondary;
  }

  &__btn {
    width: 100%;
    margin-top: 14px;
    height: 44px;
    font-weight: 600;
  }
}

@media (max-width: $breakpoint-mobile) {
  .privacy-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .privacy-retain,
  .privacy-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .privacy-pref {
    flex-wrap: wrap;

    :deep(.el-switch) {
      margin-left: auto;
    }
  }
}
</style>

<style lang="scss">
.privacy-dialog.el-dialog {
  border-radius: 20px;
  background: linear-gradient(165deg, rgba(28, 31, 40, 0.98), rgba(15, 17, 22, 0.99));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.55);
  overflow: hidden;
}

.privacy-dialog .el-dialog__header {
  margin: 0;
  padding: 20px 20px 8px;
}

.privacy-dialog .el-dialog__body {
  padding: 8px 20px 22px;
}

.privacy-dialog .el-dialog__headerbtn {
  top: 18px;
  right: 16px;
  width: 32px;
  height: 32px;
}

.privacy-dialog .el-dialog__close {
  color: $text-secondary;
}

.privacy-dialog .el-switch.is-checked .el-switch__core {
  background-color: $primary-color;
  border-color: $primary-color;
}
</style>
