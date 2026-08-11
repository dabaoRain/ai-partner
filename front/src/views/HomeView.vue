<template>
  <div v-if="bootstrapping" class="home-boot" />

  <!-- 未登录过：展示登录/注册/游客引导页 -->
  <AuthGate
    v-else-if="!appReady"
    @success="onAuthSuccess"
    @guest="enterChatAsGuest"
  />

  <div v-else class="home-view">
    <div
      v-if="isMobile && !appStore.sidebarCollapsed"
      class="home-view__mask"
      @click="appStore.closeSidebar()"
    />
    <ChatSidebar
      :partner-name="partnerName"
      :identity="identity"
      :sessions="sessions"
      :active-id="activeSessionId"
      :is-logged-in="userStore.isLoggedIn"
      :username="userStore.userInfo?.username || ''"
      :class="{ 'is-open': isMobile && !appStore.sidebarCollapsed }"
      @create="handleCreate"
      @select="handleSelect"
      @remove="removeSession"
      @open-persona="personaVisible = true"
      @open-auth="backToAuthGate"
      @logout="handleLogout"
      @open-privacy="privacyVisible = true"
    />
    <ChatPanel
      :session-id="activeSessionId"
      :messages="activeMessages"
      :sending="sending"
      @send="sendMessage"
      @stop="stopGeneration"
      @retry="retryMessage"
      @feedback="handleFeedback"
    />
    <PersonaSettingsDialog
      v-model="personaVisible"
      :persona-id="activePersonaId"
      @apply="onPersonaApply"
    />
    <PrivacySettingsDialog
      v-model="privacyVisible"
      @deleted="handleAccountDeleted"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ChatSidebar from "@/components/chat/ChatSidebar.vue";
import ChatPanel from "@/components/chat/ChatPanel.vue";
import AuthGate from "@/components/chat/AuthGate.vue";
import PersonaSettingsDialog from "@/components/chat/PersonaSettingsDialog.vue";
import PrivacySettingsDialog from "@/components/chat/PrivacySettingsDialog.vue";
import { useAppStore } from "@/store/app";
import { useUserStore } from "@/store";
import { useWindowSize } from "@/composables/useWindowSize";
import { ensureAuthReady } from "@/utils/authBootstrap";
import { claimGuest, logout as logoutApi } from "@/api/auth";
import { postFeedback, trackClientEvent } from "@/api/analytics";
import { ChatStreamError } from "@/utils/chatError";
import {
  createSession as createSessionApi,
  deleteSession,
  fetchSessionDetail,
  fetchSessions,
  sendChatStream,
  stopChat,
  updateSessionPersona,
} from "@/api/chat";
import request from "@/utils/request";

import { fetchDefaultPersona } from "@/api/persona";
import {
  normalizePersona,
  personasEqual,
} from "@/constants/personaPresets";

const appStore = useAppStore();
const userStore = useUserStore();
const { isMobile } = useWindowSize();

/** 工作区当前人设（来自官方库或会话快照） */
const workspacePersona = ref(normalizePersona({ name: "加载中" }));
const partnerName = computed(() => workspacePersona.value.name || "");
const identity = computed(() => workspacePersona.value.identity || "");
/** 当前选用的官方人设 id */
const activePersonaId = ref("");
/** 当前会话锁定的人设快照（用于检测变更） */
const sessionPersonaSnapshot = ref(null);

/** 当前工作区人设，供创建会话与发消息共用 */
function currentPersona() {
  return normalizePersona(workspacePersona.value);
}

function applyPersona(detail, personaId = "") {
  if (!detail) return;
  workspacePersona.value = normalizePersona(detail);
  if (personaId !== undefined && personaId !== null) {
    activePersonaId.value = personaId || "";
  }
}

async function ensureDefaultPersona() {
  if (activePersonaId.value && workspacePersona.value.name !== "加载中") {
    return;
  }
  const detail = await fetchDefaultPersona();
  applyPersona(detail, detail.id);
}

async function onPersonaApply({ id, persona }) {
  const next = normalizePersona(persona);
  const locked = sessionPersonaSnapshot.value;
  const hasSession = Boolean(activeSessionId.value);
  const current = sessions.value.find(
    (item) => item.id === activeSessionId.value,
  );
  const isEmptySession = Boolean(
    current && !current.messages.some((msg) => msg.role === "user"),
  );

  // 与当前会话锁定人设一致：只更新工作区引用
  if (hasSession && locked && personasEqual(next, locked)) {
    applyPersona(next, id);
    ElMessage.success("人设已应用到当前会话");
    return;
  }

  // 空会话：直接改快照，无需新建
  if (hasSession && isEmptySession && (!locked || !personasEqual(next, locked))) {
    const detail = await updateSessionPersona(activeSessionId.value, {
      persona_id: id,
    });
    applyPersona(detail, detail.persona_id || id);
    sessionPersonaSnapshot.value = normalizePersona(detail);
    const item = sessions.value.find((s) => s.id === activeSessionId.value);
    if (item) {
      item.name = detail.name || item.name;
      item.identity = detail.identity || "";
      item.tone = detail.tone || "";
      item.personaId = detail.persona_id || id || "";
      item.messages = detail.messages || [];
    }
    ElMessage.success("人设已更新到当前会话");
    return;
  }

  // 已有问答：必须新建会话
  if (hasSession && locked && !personasEqual(next, locked)) {
    try {
      await ElMessageBox.confirm(
        `当前会话已绑定人设「${locked.name || "未命名"}」，更换人设需要新建会话。是否继续？`,
        "更换人设",
        {
          type: "warning",
          confirmButtonText: "新建会话",
          cancelButtonText: "取消",
          customClass: "persona-switch-box",
          appendTo: document.body,
          center: false,
        },
      );
    } catch {
      return;
    }
    applyPersona(next, id);
    await createSession({ force: true, personaId: id });
    ElMessage.success("已用人设新建会话");
    return;
  }

  // 无会话：应用并等待用户发消息时自动建会话
  applyPersona(next, id);
  ElMessage.success("人设已应用，发送消息或新建会话后生效");
}

const sessions = ref([]);
const activeSessionId = ref("");
const sending = ref(false);
/** 是否已进入聊天主界面（已登录用户启动时直接为 true） */
const appReady = ref(false);
const bootstrapping = ref(true);
const privacyVisible = ref(false);
const personaVisible = ref(false);

/** 当前进行中的流式请求控制 */
const activeAbort = ref(null);
const activeRequestId = ref("");
const stopRequested = ref(false);

const activeMessages = computed(() => {
  const current = sessions.value.find(
    (item) => item.id === activeSessionId.value,
  );
  return current ? current.messages : [];
});

watch(
  isMobile,
  (mobile) => {
    if (mobile) {
      appStore.closeSidebar();
    } else {
      appStore.openSidebar();
    }
  },
  { immediate: true },
);

function mapSessionItem(item, messages = []) {
  return {
    id: item.session_id,
    name: item.name || "",
    identity: item.identity || "",
    tone: item.tone || "",
    personality: item.personality || "",
    personaId: item.persona_id || "",
    messages,
  };
}

async function loadSessions() {
  const list = await fetchSessions();
  const prevActive = activeSessionId.value;
  const messageMap = Object.fromEntries(
    sessions.value.map((item) => [item.id, item.messages]),
  );

  sessions.value = (list || []).map((item) =>
    mapSessionItem(item, messageMap[item.session_id] || []),
  );

  if (prevActive && sessions.value.some((item) => item.id === prevActive)) {
    activeSessionId.value = prevActive;
  } else if (!sessions.value.some((item) => item.id === activeSessionId.value)) {
    activeSessionId.value = "";
  }
}

async function enterChatWorkspace() {
  await ensureDefaultPersona();
  await loadSessions();
  appReady.value = true;
  trackClientEvent("app_open", {
    props: { logged_in: userStore.isLoggedIn },
  });
  if (!activeSessionId.value && sessions.value.length) {
    await selectSession(sessions.value[0].id);
  } else if (!sessions.value.length) {
    // 无历史会话时自动建一个，并展示人设开场白
    await createSession({ force: true });
  }
}

async function createSession(options = {}) {
  const force = Boolean(options.force);
  const personaId = options.personaId || activePersonaId.value || "";

  if (!force && activeSessionId.value) {
    const current = sessions.value.find(
      (item) => item.id === activeSessionId.value,
    );
    if (current && !current.messages.some((msg) => msg.role === "user")) {
      ElMessage.info("当前会话还没有问答，无需新建");
      return activeSessionId.value;
    }
  }

  const payload = {};
  if (personaId) {
    payload.persona_id = personaId;
  }

  const res = await createSessionApi(payload);
  await loadSessions();
  activeSessionId.value = res.session_id;

  const detail = await fetchSessionDetail(res.session_id);
  applyPersona(detail, detail.persona_id || personaId);
  sessionPersonaSnapshot.value = normalizePersona(detail);
  const created = sessions.value.find((item) => item.id === res.session_id);
  if (created) {
    created.messages = detail.messages || [];
  }
  return res.session_id;
}

async function handleCreate() {
  await createSession();
  if (isMobile.value) {
    appStore.closeSidebar();
  }
}

async function selectSession(id) {
  if (sending.value) {
    ElMessage.info("正在回复中，请稍后再切换会话");
    return;
  }
  activeSessionId.value = id;
  const detail = await fetchSessionDetail(id);
  applyPersona(detail, detail.persona_id || "");
  sessionPersonaSnapshot.value = normalizePersona(detail);

  let current = sessions.value.find((item) => item.id === id);
  if (!current) {
    await loadSessions();
    current = sessions.value.find((item) => item.id === id);
  }
  if (current) {
    current.messages = detail.messages || [];
  }
}

async function handleSelect(id) {
  await selectSession(id);
  if (isMobile.value) {
    appStore.closeSidebar();
  }
}

async function removeSession(id) {
  if (sending.value) {
    ElMessage.info("正在回复中，请稍后再删除会话");
    return;
  }

  const list = sessions.value;
  const idx = list.findIndex((item) => item.id === id);
  const isActive = activeSessionId.value === id;
  // 删除前确定「下一个」：优先同列表下一项，否则上一项
  let nextId = "";
  if (isActive && idx >= 0) {
    const neighbor = list[idx + 1] || list[idx - 1];
    nextId = neighbor?.id || "";
  }

  await deleteSession(id);
  await loadSessions();

  if (!isActive) return;

  if (nextId && sessions.value.some((item) => item.id === nextId)) {
    await selectSession(nextId);
    return;
  }
  if (sessions.value.length) {
    await selectSession(sessions.value[0].id);
    return;
  }

  activeSessionId.value = "";
  sessionPersonaSnapshot.value = null;
  ElMessage.info("暂无会话，可点击「新建会话」开始");
}

function newClientRequestId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `req_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

async function stopGeneration() {
  if (!sending.value) return;
  stopRequested.value = true;
  const requestId = activeRequestId.value;
  if (requestId) {
    try {
      await stopChat(requestId);
    } catch (error) {
      console.error(error);
    }
  }
  activeAbort.value?.abort();
}

/**
 * 发送消息；reuseUser=true 时不重复插入用户气泡（用于重试）。
 */
async function sendMessage(text, options = {}) {
  if (sending.value) return;

  const reuseUser = Boolean(options.reuseUser);
  const clientRequestId = options.clientRequestId || newClientRequestId();

  try {
    if (!activeSessionId.value) {
      await createSession();
    }
  } catch (error) {
    console.error(error);
    return;
  }

  const current = sessions.value.find(
    (item) => item.id === activeSessionId.value,
  );
  if (!current) return;

  if (!reuseUser) {
    current.messages.push({ role: "user", content: text });
  }
  current.messages.push({
    role: "assistant",
    content: "",
    status: "streaming",
  });
  const assistantMsg = current.messages[current.messages.length - 1];

  const history = current.messages.slice(0, -2).map((item) => ({
    role: item.role,
    content: item.content,
  }));

  const controller = new AbortController();
  activeAbort.value = controller;
  activeRequestId.value = clientRequestId;
  stopRequested.value = false;
  sending.value = true;

  try {
    await sendChatStream(
      {
        message: text,
        ...currentPersona(),
        session_id: activeSessionId.value,
        history,
        client_request_id: clientRequestId,
      },
      {
        signal: controller.signal,
        onChunk(chunk) {
          assistantMsg.content += chunk;
        },
      },
    );
    assistantMsg.status = "done";
    await loadSessions();
  } catch (error) {
    const chatErr =
      error instanceof ChatStreamError
        ? error
        : new ChatStreamError("UNKNOWN", error?.message || "流式回复失败", true);

    const cancelled =
      stopRequested.value || chatErr.code === "CLIENT_CANCELLED";

    if (cancelled) {
      // 停止时始终保留用户问题；有片段则落库同步，无片段也可重试
      assistantMsg.status = "cancelled";
      assistantMsg.retryable = true;
      assistantMsg.errorMessage = assistantMsg.content
        ? "已停止生成（已保留已生成内容）"
        : "已停止生成";
      ElMessage.info("已停止生成");
      if (assistantMsg.content) {
        await loadSessions();
      }
    } else if (chatErr.retryable) {
      assistantMsg.status = "failed";
      assistantMsg.retryable = true;
      assistantMsg.errorMessage = chatErr.message;
      ElMessage.error(chatErr.message);
    } else {
      // 不可重试失败：仍保留用户问题，避免输入丢失
      assistantMsg.status = "failed";
      assistantMsg.retryable = false;
      assistantMsg.errorMessage = chatErr.message;
      ElMessage.error(chatErr.message);
    }
    console.error(error);
  } finally {
    sending.value = false;
    activeAbort.value = null;
    activeRequestId.value = "";
    stopRequested.value = false;
  }
}

/** 对最后一条失败助手消息重试（不重复插入用户消息） */
async function retryMessage(assistantIndex) {
  if (sending.value) return;
  const current = sessions.value.find(
    (item) => item.id === activeSessionId.value,
  );
  if (!current) return;

  const assistantMsg = current.messages[assistantIndex];
  const userMsg = current.messages[assistantIndex - 1];
  if (
    !assistantMsg ||
    assistantMsg.role !== "assistant" ||
    !userMsg ||
    userMsg.role !== "user"
  ) {
    return;
  }

  const text = userMsg.content;
  current.messages.splice(assistantIndex, 1);
  await sendMessage(text, { reuseUser: true });
}

async function handleFeedback({ index, rating }) {
  const current = sessions.value.find(
    (item) => item.id === activeSessionId.value,
  );
  if (!current || !activeSessionId.value) return;
  const msg = current.messages[index];
  if (!msg || msg.role !== "assistant") return;

  try {
    await postFeedback({
      session_id: activeSessionId.value,
      message_key: `${activeSessionId.value}:${index}`,
      rating,
      reason: "",
    });
    msg.feedback = rating;
    ElMessage.success(rating === "up" ? "已点赞" : "已点踩");
  } catch (error) {
    console.error(error);
  }
}

function handleAccountDeleted() {
  userStore.logout();
  activeSessionId.value = "";
  sessions.value = [];
  appReady.value = false;
  privacyVisible.value = false;
}

async function enterChatAsGuest() {
  await enterChatWorkspace();
}

/** 用指定 guest 凭证统计可合并会话数（不依赖当前登录态） */
async function countGuestSessions(guestToken) {
  if (!guestToken) return 0;
  // 仍在游客工作区时，直接用本地列表，避免多余请求
  if (sessions.value.length > 0 && !userStore.accessToken) {
    return sessions.value.length;
  }
  try {
    const list = await request({
      url: "/sessions",
      method: "get",
      headers: { Authorization: `Bearer ${guestToken}` },
      silent: true,
    });
    return (list || []).length;
  } catch {
    // guest 已失效：清掉，避免登录后误带旧凭证
    userStore.setGuestToken("");
    return 0;
  }
}

/**
 * 登录/注册成功：先写入用户凭证，再按需合并匿名数据后进入聊天。
 */
async function onAuthSuccess(res) {
  const guestToken = userStore.guestToken;

  userStore.setAuthTokens({
    access_token: res.access_token,
    refresh_token: res.refresh_token,
    user: res.user,
  });

  const guestSessionCount = await countGuestSessions(guestToken);

  if (guestToken && guestSessionCount > 0) {
    try {
      await ElMessageBox.confirm(
        "是否将本机匿名体验中的会话合并到当前账号？合并后匿名侧将无法再访问这些会话。",
        "合并匿名数据",
        {
          confirmButtonText: "同意合并",
          cancelButtonText: "暂不合并",
          type: "warning",
          distinguishCancelAndClose: true,
          customClass: "persona-switch-box",
        },
      );
      const claimRes = await claimGuest({
        guest_token: guestToken,
        consent: true,
      });
      userStore.setGuestToken("");
      ElMessage.success(`已合并 ${claimRes.claimed_session_count} 个匿名会话`);
    } catch (error) {
      if (error === "cancel" || error === "close") {
        ElMessage.info("已保留匿名数据与账号隔离，未合并");
      } else {
        console.error(error);
      }
    }
  }

  activeSessionId.value = "";
  sessions.value = [];
  await enterChatWorkspace();
}

function backToAuthGate() {
  // 游客点「登录账号」：回到门禁，保留 guest 以便合并
  appReady.value = false;
}

async function handleLogout() {
  try {
    if (userStore.refreshToken) {
      await logoutApi(userStore.refreshToken);
    }
  } catch (error) {
    console.error(error);
  }
  userStore.logout();
  activeSessionId.value = "";
  sessions.value = [];
  appReady.value = false;
  ElMessage.success("已退出登录");
}

onMounted(async () => {
  try {
    // 已登录用户：直接进入聊天；未登录：停留在门禁页，不自动签发游客
    if (userStore.isLoggedIn) {
      await ensureAuthReady();
      await enterChatWorkspace();
    }
  } catch (error) {
    console.error(error);
    userStore.clearUserSession();
    appReady.value = false;
  } finally {
    bootstrapping.value = false;
  }
});
</script>

<style scoped lang="scss">
.home-boot {
  width: 100%;
  height: 100%;
  background: $bg-color;
}

.home-view {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
  background: $bg-color;
  position: relative;

  &__mask {
    position: fixed;
    inset: 0;
    z-index: 15;
    background: rgba(0, 0, 0, 0.45);
  }
}
</style>
