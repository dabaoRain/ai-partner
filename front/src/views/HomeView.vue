<template>
  <div class="home-view">
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
      :class="{ 'is-open': isMobile && !appStore.sidebarCollapsed }"
      @create="handleCreate"
      @select="handleSelect"
      @remove="removeSession"
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
import { ElMessage } from "element-plus";
import ChatSidebar from "@/components/chat/ChatSidebar.vue";
import ChatPanel from "@/components/chat/ChatPanel.vue";
import { useAppStore } from "@/store/app";
import { useWindowSize } from "@/composables/useWindowSize";
import {
  createSession as createSessionApi,
  deleteSession,
  fetchSessionDetail,
  fetchSessions,
  sendChatStream,
} from "@/api/chat";

const appStore = useAppStore();
const { isMobile } = useWindowSize();

const partnerName = ref("小美");
const personality = ref("温柔可爱一口台湾腔的台湾妹子");

const sessions = ref([]);
const activeSessionId = ref("");
const sending = ref(false);

const activeMessages = computed(() => {
  const current = sessions.value.find(
    (item) => item.id === activeSessionId.value,
  );
  return current ? current.messages : [];
});

// 宽屏强制展开侧栏；切到窄屏时收起
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

/** 从后端 sessions 目录同步历史列表（已按时间倒序） */
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

async function createSession() {
  // 当前会话已存在且还没有任何问答时，不再重复创建
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

  // 先删 sessions 目录下对应文件
  await deleteSession(id);

  if (isActive) {
    // 删的是当前会话：清空选中态与问答列表
    activeSessionId.value = "";
  }

  // 同步历史列表；非当前会话删除时，当前问答通过 messageMap 保留
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

  // 先写入用户消息，再插入空的 assistant 气泡用于流式追加
  current.messages.push({ role: "user", content: text });
  current.messages.push({ role: "assistant", content: "" });
  const assistantMsg = current.messages[current.messages.length - 1];

  // 历史不含本轮 user/assistant，交给后端拼进 messages
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
    // 回滚本轮 user + assistant
    current.messages.splice(-2, 2);
    ElMessage.error(error?.message || "流式回复失败");
    console.error(error);
  } finally {
    sending.value = false;
  }
}

onMounted(() => {
  loadSessions()
    .then(async () => {
      if (!activeSessionId.value && sessions.value.length) {
        await selectSession(sessions.value[0].id);
      }
    })
    .catch((error) => {
      console.error(error);
    });
});
</script>

<style scoped lang="scss">
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
