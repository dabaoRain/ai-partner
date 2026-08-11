<template>
  <el-dialog
    :model-value="modelValue"
    width="920px"
    align-center
    destroy-on-close
    class="persona-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="persona-hero">
        <div class="persona-hero__badge" aria-hidden="true">
          <el-icon :size="20"><User /></el-icon>
        </div>
        <div class="persona-hero__text">
          <h2 class="persona-hero__title">官方人设</h2>
          <p class="persona-hero__desc">
            选择并应用到会话 · 内容只读 · 有问答后需新建会话才能更换
          </p>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="persona-layout">
      <aside class="persona-library">
        <div class="persona-library__head">
          <span>人设库</span>
          <span class="persona-library__count">{{ items.length }}</span>
        </div>
        <ul v-if="items.length" class="persona-library__list">
          <li
            v-for="item in items"
            :key="item.id"
            class="persona-library__item"
            :class="{
              'is-active': item.id === selectedId,
              'is-in-use': item.id === personaId,
            }"
            @click="selectedId = item.id"
          >
            <div class="persona-library__name">
              <PersonaAvatar
                v-if="item.avatar_url"
                class="persona-library__thumb"
                :url="item.avatar_url"
                :alt="item.name"
              />
              <span class="persona-library__name-text">{{ item.name }}</span>
              <span v-if="item.id === personaId" class="persona-library__badge">使用中</span>
            </div>
            <div class="persona-library__meta">
              {{ item.region || '官方人设' }}
            </div>
          </li>
        </ul>
        <div v-else class="persona-library__empty">暂无官方人设</div>
      </aside>

      <div v-if="selected" ref="detailPanelRef" class="persona-detail">
        <header class="persona-detail__head">
          <div class="persona-detail__portrait" v-if="selected.avatar_url">
            <PersonaAvatar
              class="persona-detail__portrait-img"
              :url="selected.avatar_url"
              :alt="selected.name"
            />
          </div>
          <div class="persona-detail__titles">
            <h3 class="persona-detail__name">{{ selected.name }}</h3>
            <div class="persona-detail__tags">
              <span v-if="selected.age" class="persona-pill">{{ selected.age }}岁</span>
              <span v-if="selected.region" class="persona-pill">{{ selected.region }}</span>
              <span v-if="selected.metaphor" class="persona-pill persona-pill--accent">
                隐喻 · {{ selected.metaphor }}
              </span>
            </div>
          </div>
        </header>

        <section class="persona-block">
          <div class="persona-block__title">身份</div>
          <p class="persona-block__body">{{ selected.identity }}</p>
        </section>

        <section class="persona-block">
          <div class="persona-block__title">语气</div>
          <p class="persona-block__body">{{ selected.tone }}</p>
        </section>

        <section v-if="catchphrases.length" class="persona-block">
          <div class="persona-block__title">口头禅</div>
          <div class="persona-quotes">
            <span v-for="(line, idx) in catchphrases" :key="idx" class="persona-quote">
              {{ line }}
            </span>
          </div>
        </section>

        <section v-if="interestRows.length" class="persona-block">
          <div class="persona-block__title">兴趣爱好</div>
          <div class="persona-interest">
            <div
              v-for="row in interestRows"
              :key="row.label"
              class="persona-interest__row"
            >
              <span class="persona-interest__label">{{ row.label }}</span>
              <span class="persona-interest__value">{{ row.value }}</span>
            </div>
          </div>
        </section>

        <section v-if="stages.length" class="persona-block">
          <div class="persona-block__title">亲密阶段</div>
          <ol class="persona-stages">
            <li v-for="(stage, idx) in stages" :key="idx" class="persona-stages__item">
              <div class="persona-stages__rail" aria-hidden="true">
                <span class="persona-stages__dot" />
              </div>
              <div class="persona-stages__content">
                <div class="persona-stages__meta">
                  <strong>{{ stage.title }}</strong>
                  <span class="persona-pill persona-pill--soft">{{ stage.period }}</span>
                </div>
                <p class="persona-stages__desc">{{ stage.description }}</p>
              </div>
            </li>
          </ol>
        </section>

        <section v-if="selected.relationship_boundary" class="persona-block">
          <div class="persona-block__title">关系硬边界</div>
          <p class="persona-block__body">{{ selected.relationship_boundary }}</p>
        </section>

        <section v-if="selected.taboos" class="persona-block">
          <div class="persona-block__title">禁忌</div>
          <p class="persona-block__body persona-block__body--warn">{{ selected.taboos }}</p>
        </section>

        <section v-if="selected.personality" class="persona-block">
          <div class="persona-block__title">补充性格</div>
          <p class="persona-block__body">{{ selected.personality }}</p>
        </section>

        <section v-if="openings.length" class="persona-block">
          <div class="persona-block__title">开场白</div>
          <div class="persona-quotes">
            <span v-for="(line, idx) in openings" :key="idx" class="persona-quote">
              {{ line }}
            </span>
          </div>
        </section>

        <section v-if="eggs.length" class="persona-block">
          <div class="persona-block__title">彩蛋触发</div>
          <ul class="persona-eggs">
            <li v-for="(egg, idx) in eggs" :key="idx" class="persona-eggs__item">
              <span class="persona-eggs__trigger">{{ egg.trigger }}</span>
              <span class="persona-eggs__arrow" aria-hidden="true">→</span>
              <span class="persona-eggs__response">{{ egg.response }}</span>
            </li>
          </ul>
        </section>
      </div>
      <div v-else class="persona-detail persona-detail--empty">请选择左侧人设查看详情</div>
    </div>

    <template #footer>
      <div class="persona-footer">
        <p class="persona-footer__hint">
          {{
            selected
              ? `将应用「${selected.name}」到当前工作区`
              : '请先选择一个人设'
          }}
        </p>
        <div class="persona-footer__actions">
          <el-button @click="close">关闭</el-button>
          <el-button
            type="primary"
            :disabled="!selected"
            :loading="busy"
            @click="applySelected"
          >
            应用此人设
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import { fetchPersonas } from '@/api/persona'
import { normalizePersona } from '@/constants/personaPresets'
import PersonaAvatar from '@/components/chat/PersonaAvatar.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  /** 当前会话/工作区使用的人设 id */
  personaId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'apply'])

const loading = ref(false)
const busy = ref(false)
const items = ref([])
const selectedId = ref('')
const detailPanelRef = ref(null)

const selected = computed(() => items.value.find((item) => item.id === selectedId.value) || null)

const catchphrases = computed(() =>
  Array.isArray(selected.value?.catchphrases) ? selected.value.catchphrases : [],
)
const openings = computed(() =>
  Array.isArray(selected.value?.openings) ? selected.value.openings : [],
)
const stages = computed(() =>
  Array.isArray(selected.value?.intimacy_stages) ? selected.value.intimacy_stages : [],
)
const eggs = computed(() =>
  Array.isArray(selected.value?.easter_eggs) ? selected.value.easter_eggs : [],
)

/** 兴趣爱好拆成 深度热爱 / 日常消遣 / 冷门癖好 行 */
const interestRows = computed(() => {
  const raw = (selected.value?.interests || '').trim()
  if (!raw) return []
  const rows = []
  for (const line of raw.split('\n')) {
    const text = line.trim()
    if (!text) continue
    const matched = text.match(/^(深度热爱|日常消遣|冷门癖好)[:：]\s*(.+)$/)
    if (matched) {
      rows.push({ label: matched[1], value: matched[2] })
    } else {
      rows.push({ label: '兴趣', value: text.replace(/^[-•]\s*/, '') })
    }
  }
  return rows
})

async function loadItems() {
  loading.value = true
  try {
    const list = await fetchPersonas()
    items.value = Array.isArray(list) ? list : []
    if (!items.value.length) {
      selectedId.value = ''
      return
    }
    const prefer =
      items.value.find((item) => item.id === props.personaId) || items.value[0]
    selectedId.value = prefer.id
  } catch (err) {
    ElMessage.error(err?.message || '加载人设失败')
  } finally {
    loading.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}

async function applySelected() {
  if (!selected.value) return
  busy.value = true
  try {
    emit('apply', {
      id: selected.value.id,
      persona: normalizePersona(selected.value),
    })
    close()
  } finally {
    busy.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) loadItems()
  },
)

watch(selectedId, () => {
  // 切换人设时详情滚回顶部
  requestAnimationFrame(() => {
    if (detailPanelRef.value) detailPanelRef.value.scrollTop = 0
  })
})
</script>

<style scoped lang="scss">
.persona-hero {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding-right: 28px;

  &__badge {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    background: rgba(255, 90, 42, 0.14);
    color: $primary-soft;
    flex-shrink: 0;
  }

  &__title {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.3;
    color: $text-color;
  }

  &__desc {
    margin: 4px 0 0;
    font-size: 13px;
    color: $text-secondary;
    line-height: 1.45;
  }
}

.persona-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 14px;
  height: min(62vh, 560px);
  min-height: 320px;
  overflow: hidden;
}

.persona-library {
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: rgba(0, 0, 0, 0.18);

  &__head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    font-size: 12px;
    font-weight: 650;
    letter-spacing: 0.04em;
    color: $text-secondary;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  &__count {
    min-width: 22px;
    height: 22px;
    padding: 0 6px;
    border-radius: 999px;
    display: inline-grid;
    place-items: center;
    font-size: 11px;
    font-weight: 600;
    color: $text-color;
    background: rgba(255, 255, 255, 0.08);
  }

  &__list {
    list-style: none;
    margin: 0;
    padding: 8px;
    overflow-x: hidden;
    overflow-y: auto;
    flex: 1 1 auto;
    min-height: 0;
    overscroll-behavior: contain;
  }

  &__item {
    position: relative;
    padding: 10px 12px 10px 14px;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.15s ease;

    &::before {
      content: '';
      position: absolute;
      left: 4px;
      top: 12px;
      bottom: 12px;
      width: 2px;
      border-radius: 2px;
      background: transparent;
    }

    &:hover {
      background: rgba(255, 255, 255, 0.04);
    }

    &.is-active {
      background: rgba(255, 90, 42, 0.12);

      &::before {
        background: $primary-color;
      }
    }
  }

  &__name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 650;
    color: $text-color;
  }

  &__thumb {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    object-fit: cover;
    flex-shrink: 0;
    background: rgba(255, 255, 255, 0.06);
  }

  &__name-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__badge {
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 999px;
    background: $primary-color;
    color: #fff;
  }

  &__meta {
    margin-top: 3px;
    font-size: 12px;
    color: $text-secondary;
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__empty {
    padding: 24px 16px;
    text-align: center;
    color: $text-secondary;
    font-size: 13px;
  }
}

.persona-detail {
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 16px 18px 20px;
  min-height: 0;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  background: rgba(255, 255, 255, 0.02);

  &--empty {
    display: grid;
    place-items: center;
    color: $text-secondary;
  }

  &__head {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 16px;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  &__portrait {
    width: 88px;
    height: 112px;
    border-radius: 12px;
    overflow: hidden;
    flex-shrink: 0;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  &__portrait-img {
    width: 100%;
    height: 100%;
  }

  &__titles {
    min-width: 0;
    flex: 1;
  }

  &__name {
    margin: 0;
    font-size: 22px;
    font-weight: 720;
    letter-spacing: 0.02em;
    color: $text-color;
  }

  &__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }
}

.persona-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.4;
  color: $text-secondary;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.05);

  &--accent {
    color: #ffc4b0;
    background: rgba(255, 90, 42, 0.12);
    border-color: rgba(255, 90, 42, 0.22);
  }

  &--soft {
    color: $text-secondary;
    background: rgba(255, 255, 255, 0.05);
    font-weight: 500;
  }
}

.persona-block {
  & + & {
    margin-top: 18px;
  }

  &__title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: none;
    color: $text-secondary;
    margin-bottom: 8px;
  }

  &__body {
    margin: 0;
    font-size: 13.5px;
    line-height: 1.7;
    color: $text-color;
    white-space: pre-wrap;

    &--warn {
      color: #ffc9c2;
    }
  }
}

.persona-quotes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.persona-quote {
  display: block;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.55;
  color: $text-color;
  background: rgba(255, 255, 255, 0.04);
  border-left: 2px solid rgba(255, 90, 42, 0.55);
}

.persona-interest {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__row {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 10px;
    align-items: start;
    padding: 10px 12px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.035);
  }

  &__label {
    font-size: 12px;
    font-weight: 650;
    color: $primary-soft;
    line-height: 1.5;
  }

  &__value {
    font-size: 13px;
    line-height: 1.55;
    color: $text-color;
  }
}

.persona-stages {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0;

  &__item {
    display: grid;
    grid-template-columns: 18px minmax(0, 1fr);
    gap: 10px;
  }

  &__rail {
    position: relative;
    display: flex;
    justify-content: center;
    padding-top: 6px;

    &::after {
      content: '';
      position: absolute;
      top: 16px;
      bottom: -6px;
      width: 1px;
      background: rgba(255, 255, 255, 0.1);
    }
  }

  &__item:last-child .persona-stages__rail::after {
    display: none;
  }

  &__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: $primary-color;
    box-shadow: 0 0 0 3px rgba(255, 90, 42, 0.18);
    z-index: 1;
  }

  &__content {
    padding: 0 0 14px;
  }

  &__meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;

    strong {
      font-size: 13.5px;
      font-weight: 700;
      color: $text-color;
    }
  }

  &__desc {
    margin: 0;
    font-size: 13px;
    line-height: 1.6;
    color: $text-secondary;
  }
}

.persona-eggs {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__item {
    display: grid;
    grid-template-columns: auto 16px minmax(0, 1fr);
    gap: 8px;
    align-items: start;
    padding: 10px 12px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.035);
    font-size: 13px;
    line-height: 1.55;
  }

  &__trigger {
    font-weight: 650;
    color: $primary-soft;
    white-space: nowrap;
  }

  &__arrow {
    color: $text-secondary;
    text-align: center;
  }

  &__response {
    color: $text-color;
  }
}

.persona-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;

  &__hint {
    margin: 0;
    font-size: 12px;
    color: $text-secondary;
    line-height: 1.4;
  }

  &__actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

@media (max-width: $breakpoint-mobile) {
  .persona-layout {
    grid-template-columns: 1fr;
    height: min(70vh, 640px);
    grid-template-rows: 160px minmax(0, 1fr);
  }

  .persona-library {
    height: 100%;
    max-height: none;
  }

  .persona-interest__row {
    grid-template-columns: 1fr;
    gap: 4px;
  }

  .persona-footer {
    flex-direction: column;
    align-items: stretch;

    &__actions {
      justify-content: flex-end;
    }
  }
}
</style>

<style lang="scss">
/* 遮罩层双轴居中（覆盖 EP 默认 margin-top: 15vh） */
.el-overlay-dialog:has(.persona-dialog) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.persona-dialog.el-dialog {
  display: flex;
  flex-direction: column;
  margin: 0 !important;
  max-height: min(92vh, 860px);
  border-radius: 20px;
  background: linear-gradient(165deg, rgba(28, 31, 40, 0.98), rgba(15, 17, 22, 0.99));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.55);
  overflow: hidden;
}

.persona-dialog .el-dialog__header {
  margin: 0;
  padding: 20px 20px 10px;
  flex-shrink: 0;
}

.persona-dialog .el-dialog__body {
  padding: 4px 20px 8px;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.persona-dialog .el-dialog__footer {
  padding: 12px 20px 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  background: rgba(15, 17, 22, 0.98);
}

.persona-dialog .el-dialog__headerbtn {
  top: 18px;
  right: 16px;
  width: 32px;
  height: 32px;
}

.persona-dialog .el-dialog__close {
  color: $text-secondary;
}

.persona-dialog .el-button--default {
  --el-button-bg-color: #2a2e38;
  --el-button-border-color: #{$border-color};
  --el-button-text-color: #{$text-color};
  background-color: #2a2e38 !important;
  border-color: $border-color !important;
  color: $text-color !important;
}

.persona-dialog .el-button--primary {
  background-color: $primary-color !important;
  border-color: $primary-color !important;
}

/* 让滚动条在暗色面板上更易察觉 */
.persona-dialog .persona-library__list,
.persona-dialog .persona-detail {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.28) transparent;
}

.persona-dialog .persona-library__list::-webkit-scrollbar,
.persona-dialog .persona-detail::-webkit-scrollbar {
  width: 8px;
}

.persona-dialog .persona-library__list::-webkit-scrollbar-thumb,
.persona-dialog .persona-detail::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.28);
  border-radius: 999px;
}

.persona-dialog .persona-library__list::-webkit-scrollbar-track,
.persona-dialog .persona-detail::-webkit-scrollbar-track {
  background: transparent;
}
</style>
