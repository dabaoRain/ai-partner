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
      v-model:name="partnerName"
      v-model:personality="personality"
      :sessions="sessions"
      :active-id="activeSessionId"
      :is-logged-in="userStore.isLoggedIn"
      :username="userStore.userInfo?.username || ''"
      :class="{ 'is-open': isMobile && !appStore.sidebarCollapsed }"
      @create="handleCreate"
      @select="handleSelect"
      @remove="removeSession"
      @open-auth="backToAuthGate"
      @logout="handleLogout"
    />
    <ChatPanel
      :session-id="activeSessionId"
      :messages="activeMessages"
      :sending="sending"
      @send="sendMessage"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ChatSidebar from "@/components/chat/ChatSidebar.vue";
import ChatPanel from "@/components/chat/ChatPanel.vue";
import AuthGate from "@/components/chat/AuthGate.vue";
import { useAppStore } from "@/store/app";
import { useUserStore } from "@/store";
import { useWindowSize } from "@/composables/useWindowSize";
import { ensureAuthReady } from "@/utils/authBootstrap";
import { claimGuest, logout as logoutApi } from "@/api/auth";
import {
  createSession as createSessionApi,
  deleteSession,
  fetchSessionDetail,
  fetchSessions,
  sendChatStream,
} from "@/api/chat";

const appStore = useAppStore();
const userStore = useUserStore();
const { isMobile } = useWindowSize();

const partnerName = ref("小美");
const personality = ref("温柔可爱一口台湾腔的台湾妹子");

const sessions = ref([]);
const activeSessionId = ref("");
const sending = ref(false);
/** 是否已进入聊天主界面（已登录用户启动时直接为 true） */
const appReady = ref(false);
const bootstrapping = ref(true);

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
    personality: item.personality || "",
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
  if (!activeSessionId.value && sessions.value.length) {
    await selectSession(sessions.value[0].id);
  }
}

async function createSession() {
  if (activeSessionId.value) {
    const current = sessions.value.find(
      (item) => item.id === activeSessionId.value,
    );
    if (current && current.messages.length === 0) {
      ElMessage.info("当前会话还没有问答，无需新建");
      return activeSessionId.value;
    }
  }

  const res = await createSessionApi({
    name: partnerName.value,
    personality: personality.value,
  });
  await loadSessions();
  activeSessionId.value = res.session_id;
  const created = sessions.value.find((item) => item.id === res.session_id);
  if (created) {
    created.messages = [];
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
  partnerName.value = detail.name || partnerName.value;
  personality.value = detail.personality || personality.value;

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
  const isActive = activeSessionId.value === id;
  await deleteSession(id);

  if (isActive) {
    activeSessionId.value = "";
  }

  await loadSessions();

  if (isActive && !sessions.value.length) {
    ElMessage.info("暂无会话，可点击「新建会话」开始");
  }
}

async function sendMessage(text) {
  if (sending.value) return;

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

  current.messages.push({ role: "user", content: text });
  current.messages.push({ role: "assistant", content: "" });
  const assistantMsg = current.messages[current.messages.length - 1];

  const history = current.messages.slice(0, -2).map((item) => ({
    role: item.role,
    content: item.content,
  }));

  sending.value = true;
  try {
    await sendChatStream(
      {
        message: text,
        name: partnerName.value,
        personality: personality.value,
        session_id: activeSessionId.value,
        history,
      },
      {
        onChunk(chunk) {
          assistantMsg.content += chunk;
        },
      },
    );
    await loadSessions();
  } catch (error) {
    current.messages.splice(-2, 2);
    ElMessage.error(error?.message || "流式回复失败");
    console.error(error);
  } finally {
    sending.value = false;
  }
}

async function enterChatAsGuest() {
  await enterChatWorkspace();
}

/** 切换登录态前，用当前 guest 凭证统计是否有可合并会话 */
async function countGuestSessions(guestToken) {
  if (!guestToken) return 0;
  if (sessions.value.length > 0 && !userStore.accessToken) {
    return sessions.value.length;
  }
  try {
    // 此时尚未写入用户 token，interceptor 会带上 guest
    const list = await fetchSessions();
    return (list || []).length;
  } catch {
    return 0;
  }
}

/**
 * 登录/注册成功：写入凭证，按需合并匿名数据后进入聊天。
 */
async function onAuthSuccess(res) {
  const guestToken = userStore.guestToken;
  const guestSessionCount = await countGuestSessions(guestToken);

  userStore.setAuthTokens({
    access_token: res.access_token,
    refresh_token: res.refresh_token,
    user: res.user,
  });

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
