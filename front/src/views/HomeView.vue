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
      :sessions="sessions"
      :active-id="activeSessionId"
      :is-logged-in="userStore.isLoggedIn"
      :username="userStore.userInfo?.username || ''"
      :class="{ 'is-open': isMobile && !appStore.sidebarCollapsed }"
      @select="handleSelect"
      @session-action="handleSessionAction"
      @open-persona="personaVisible = true"
      @open-auth="backToAuthGate"
      @logout="handleLogout"
      @open-privacy="privacyVisible = true"
    />
    <ChatPanel
      :session-id="activeSessionId"
      :messages="activeMessages"
      :sending="sending"
      :partner-avatar="workspacePersona.avatar_url"
      :partner-name="partnerName"
      :partner-meta="partnerMeta"
      :can-compose="Boolean(activePersonaId)"
      @choose-persona="personaVisible = true"
      @start="handleStartConversation"
      @send="sendMessage"
      @stop="stopGeneration"
      @retry="retryMessage"
      @message-action="handleMessageAction"
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
} from "@/api/chat";
import request from "@/utils/request";

import { normalizePersona } from "@/constants/personaPresets";

const appStore = useAppStore();
const userStore = useUserStore();
const { isMobile } = useWindowSize();

/** 工作区当前人设（来自用户选择或会话快照；无对话时不预选） */
const workspacePersona = ref(normalizePersona({}));
const partnerName = computed(() => workspacePersona.value.name || "");
const partnerMeta = computed(() => {
  const persona = workspacePersona.value;
  if (!persona.name) return "";
  return persona.motto || "官方伴侣";
});
/** 当前选用的官方人设 id；空表示尚未选择 */
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

/** 清空工作区人设（无对话冷启动） */
function clearWorkspacePersona() {
  workspacePersona.value = normalizePersona({});
  activePersonaId.value = "";
  sessionPersonaSnapshot.value = null;
}

/** 按人设 id 查找关系线 */
function findSessionByPersona(personaId) {
  const key = (personaId || "").trim();
  if (!key) return null;
  return sessions.value.find((item) => (item.personaId || "") === key) || null;
}

/**
 * 选择伴侣：有线则打开；无线则进入空态，等用户在主区开始关系
 */
async function onPersonaApply({ id, persona }) {
  const next = normalizePersona(persona);
  const existing = findSessionByPersona(id);

  applyPersona(next, id);

  if (existing) {
    await selectSession(existing.id);
    ElMessage.success(`已打开与「${next.name || "该人设"}」的对话`);
    return;
  }

  activeSessionId.value = "";
  sessionPersonaSnapshot.value = null;
  ElMessage.success(
    `已选择「${next.name || "该人设"}」，可以开始和 TA 聊天了`,
  );
}

/** 会话列表展示名：人设姓名（关系线模型一人设一线） */
function formatSessionTitle(name) {
  return (name || "").trim() || "未命名";
}

function patchSessionItemFromDetail(item, detail, personaId = "") {
  item.name = detail.name || item.name;
  item.identity = detail.identity || "";
  item.motto = detail.motto || "";
  item.tone = detail.tone || "";
  item.region = detail.region || "";
  item.avatarUrl = detail.avatar_url || item.avatarUrl || "";
  item.personaId = detail.persona_id || personaId || item.personaId || "";
  item.createdAt = detail.created_at || item.createdAt || "";
  item.updatedAt = detail.updated_at || item.updatedAt || "";
  item.messages = detail.messages || item.messages || [];
  item.title = formatSessionTitle(item.name);
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
  const name = item.name || "";
  return {
    id: item.session_id,
    name,
    title: formatSessionTitle(name),
    identity: item.identity || "",
    motto: item.motto || "",
    tone: item.tone || "",
    region: item.region || "",
    avatarUrl: item.avatar_url || "",
    personality: item.personality || "",
    personaId: item.persona_id || "",
    createdAt: item.created_at || "",
    updatedAt: item.updated_at || "",
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
  await loadSessions();
  appReady.value = true;
  trackClientEvent("app_open", {
    props: { logged_in: userStore.isLoggedIn },
  });
  if (!activeSessionId.value && sessions.value.length) {
    // 再次进入：打开最近更新的关系线（人设来自该对话）
    await selectSession(sessions.value[0].id);
  } else if (!sessions.value.length) {
    // 无对话：不预选默认人设，须手动选择伴侣
    activeSessionId.value = "";
    clearWorkspacePersona();
  }
}

/**
 * 打开或创建当前工作区人设的关系线。
 * @param {{ reset?: boolean }} options
 */
async function openOrStartConversation(options = {}) {
  const reset = Boolean(options.reset);
  const personaId = activePersonaId.value || "";
  if (!personaId) {
    ElMessage.warning("请先选择伴侣人设");
    return "";
  }

  const payload = { persona_id: personaId, reset };
  const res = await createSessionApi(payload);
  await loadSessions();
  activeSessionId.value = res.session_id;

  const detail = await fetchSessionDetail(res.session_id);
  applyPersona(detail, detail.persona_id || personaId);
  sessionPersonaSnapshot.value = normalizePersona(detail);
  const row = sessions.value.find((item) => item.id === res.session_id);
  if (row) {
    patchSessionItemFromDetail(row, detail, personaId);
  }
  return res.session_id;
}

/** 主区 CTA：开始/打开当前伴侣关系线 */
async function handleStartConversation() {
  if (!activePersonaId.value) {
    personaVisible.value = true;
    ElMessage.info("请先选择一位伴侣");
    return "";
  }

  const personaId = activePersonaId.value;
  const personaName = partnerName.value || "该人设";
  const existing = findSessionByPersona(personaId);

  if (!existing) {
    const sessionId = await openOrStartConversation({ reset: false });
    ElMessage.success(`已开始与「${personaName}」的对话`);
    if (isMobile.value) appStore.closeSidebar();
    return sessionId;
  }

  if (existing.id !== activeSessionId.value) {
    await selectSession(existing.id);
    ElMessage.success(`已打开与「${personaName}」的对话`);
    if (isMobile.value) appStore.closeSidebar();
    return existing.id;
  }

  return existing.id;
}

async function selectSession(id) {
  if (sending.value) {
    ElMessage.info("正在回复中，请稍后再切换对话");
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
    patchSessionItemFromDetail(current, detail, detail.persona_id || "");
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
    ElMessage.info("正在回复中，请稍后再删除");
    return;
  }

  const target = sessions.value.find((item) => item.id === id);
  const name = target?.name || "该人设";
  try {
    await ElMessageBox.confirm(
      `将清空与「${name}」的聊天记录，之后可重新开始。当前伴侣选择会保留，聊天记录不可恢复。`,
      "清空聊天记录",
      {
        type: "warning",
        confirmButtonText: "清空记录",
        cancelButtonText: "取消",
        customClass: "persona-switch-box",
        appendTo: document.body,
      },
    );
  } catch {
    return;
  }

  const isActive = activeSessionId.value === id;
  await deleteSession(id);
  await loadSessions();

  if (!isActive) return;

  // 保留工作区人设，进入空态
  activeSessionId.value = "";
  sessionPersonaSnapshot.value = null;
  ElMessage.info("聊天记录已清空，可重新开始");
}

async function resetSession(id) {
  if (sending.value) {
    ElMessage.info("正在回复中，请稍后再重置");
    return;
  }

  const target = sessions.value.find((item) => item.id === id);
  const personaId = target?.personaId || "";
  const name = target?.name || "该人设";
  if (!personaId) {
    ElMessage.warning("该伴侣缺少人设信息，无法重置");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `将清空与「${name}」的聊天记录，并重新生成开场白。聊天记录不可恢复。`,
      "清空并重开",
      {
        type: "warning",
        confirmButtonText: "清空并重开",
        cancelButtonText: "取消",
        customClass: "persona-switch-box",
        appendTo: document.body,
      },
    );
  } catch {
    return;
  }

  const res = await createSessionApi({ persona_id: personaId, reset: true });
  await loadSessions();
  activeSessionId.value = res.session_id;

  const detail = await fetchSessionDetail(res.session_id);
  applyPersona(detail, detail.persona_id || personaId);
  sessionPersonaSnapshot.value = normalizePersona(detail);
  const row = sessions.value.find((item) => item.id === res.session_id);
  if (row) {
    patchSessionItemFromDetail(row, detail, personaId);
  }
  ElMessage.success(`已重新开始与「${name}」的聊天`);
  if (isMobile.value) appStore.closeSidebar();
}

async function rateSession(id) {
  const target = sessions.value.find((item) => item.id === id);
  const name = target?.name || "该伴侣";
  try {
    const { value } = await ElMessageBox.prompt(
      `这次和「${name}」的聊天体验如何？可以写下感受或问题。`,
      "评价本次聊天",
      {
        confirmButtonText: "提交评价",
        cancelButtonText: "取消",
        inputPlaceholder: "例如：很像人设 / 回复太机械 / 没有安慰到我 / 上下文不对",
        inputType: "textarea",
        customClass: "persona-switch-box",
      },
    );
    await trackClientEvent("session_feedback", {
      session_id: id,
      props: {
        persona_id: target?.personaId || "",
        persona_name: name,
        note: value || "",
      },
    });
    ElMessage.success("已收到评价");
  } catch {
    // 用户取消
  }
}

async function handleSessionAction({ id, command }) {
  if (command === "rate") {
    await rateSession(id);
    return;
  }
  if (command === "reset") {
    await resetSession(id);
    return;
  }
  if (command === "clear") {
    await removeSession(id);
  }
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
 * 无会话时：开始/打开当前人设关系线（与主区开始关系等价）。
 */
async function sendMessage(text, options = {}) {
  if (sending.value) return;

  const reuseUser = Boolean(options.reuseUser);
  const clientRequestId = options.clientRequestId || newClientRequestId();

  try {
    if (!activePersonaId.value) {
      personaVisible.value = true;
      ElMessage.info("请先选择一位伴侣");
      return;
    }
    if (!activeSessionId.value) {
      await openOrStartConversation({ reset: false });
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

async function copyMessageContent(content) {
  const text = (content || "").trim();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制");
  } catch (error) {
    console.error(error);
    ElMessage.error("复制失败，请手动选择文本复制");
  }
}

async function handleMessageAction({ index, action }) {
  const current = sessions.value.find(
    (item) => item.id === activeSessionId.value,
  );
  if (!current) return;
  const msg = current.messages[index];
  if (!msg || msg.role !== "assistant") return;

  if (action === "copy") {
    await copyMessageContent(msg.content);
    return;
  }

  if (action === "regenerate") {
    await retryMessage(index);
    return;
  }

  if (action === "feedback") {
    try {
      const { value } = await ElMessageBox.prompt(
        "请简单说说这条回复哪里不符合预期，帮助我们改进问答体验。",
        "反馈这条回复",
        {
          confirmButtonText: "提交反馈",
          cancelButtonText: "取消",
          inputPlaceholder: "例如：不符合人设 / 没理解我 / 太啰嗦 / 情绪支持不好",
          inputType: "textarea",
          customClass: "persona-switch-box",
        },
      );
      await handleFeedback({ index, rating: "down", reason: value || "" });
    } catch {
      // 用户取消
    }
  }
}

async function handleFeedback({ index, rating, reason = "" }) {
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
      reason,
    });
    msg.feedback = rating;
    ElMessage.success("已收到反馈");
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
