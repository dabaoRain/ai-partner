# AI智能伴侣 · 项目说明（V1.0.0）

本文汇总本项目从初始化到功能落地的要点，便于本地开发、简历展示与后续迭代。

---

## 1. 项目是什么

暗色双栏「AI 智能伴侣」Demo：左侧控制面板（新建/历史会话、名字、性格），右侧聊天区（流式回复、按住说话）。

面向场景：个人学习 / 简历可演示项目。大模型使用 DeepSeek API。

---

## 2. 技术栈

| 端 | 技术 |
|----|------|
| 前端 | Vue 3、Vite 5、Element Plus、Vue Router、Pinia、SCSS、pnpm |
| 后端 | FastAPI、Uvicorn、OpenAI SDK（DeepSeek 兼容）、python-dotenv |
| 语音 | 浏览器 Web Speech API（前端独立识别，不经自建后端 ASR） |

依赖管理：前端 `pnpm`；后端 `back/.venv` + `requirements.txt`。

---

## 3. 目录结构（精简）

```
AI-Partner/
├── front/                 # 前端
│   ├── src/
│   │   ├── api/           # 接口（含 SSE 流式聊天）
│   │   ├── components/chat/
│   │   ├── composables/   # 含 useSpeechRecognition
│   │   ├── views/HomeView.vue
│   │   └── ...
│   ├── .env.development
│   └── .env.production
├── back/                  # 后端
│   ├── main.py            # 入口：中间件 + 挂载路由
│   ├── config.py          # 环境变量、路径、模型名
│   ├── schemas.py         # 请求/响应模型
│   ├── session_store.py   # sessions 目录读写
│   ├── llm.py             # DeepSeek 客户端与提示词
│   ├── routers/           # health / sessions / chat
│   ├── sessions/          # 会话 JSON 落盘
│   └── .env               # DEEPSEEK_API_KEY（勿提交）
├── deploy/                # Nginx / systemd 等部署模板
└── docs/                  # 文档（含本文、部署说明）
```

---

## 4. 核心链路

### 4.1 文字聊天（流式）

```
输入 / 语音转文字
  → HomeView.sendMessage
  → POST /api/chat（SSE）
  → DeepSeek stream=True
  → 前端逐块追加到 assistant 气泡
  → 流结束后写入 sessions/{session_id}.json
```

- 空气泡等待首包时展示「思考中」动画。
- 人设（名字、性格）每轮随请求传入，写入 system 提示词，**不写死在后端**。

### 4.2 会话

- `session_id` **由后端生成**（格式 `年月日_时分秒`），同时作为 JSON 文件名。
- `POST /sessions`：创建空会话文件。
- `GET /sessions`：扫描 `sessions/`，按 id 倒序（最新在上）。
- `GET /sessions/{id}`：详情（含 turns → messages）。
- `DELETE /sessions/{id}`：删文件。
- 当前会话已存在且无问答时，重复点「新建会话」不会再创建。
- 删除当前会话：清空问答列表；删除其他会话：保留当前问答，只删对应文件。

### 4.3 会话 JSON 结构

顶层：`session_id`、`name`、`personality`、`created_at`、`updated_at`。  
`turns` 内只保留：`question`、`answer`、`saved_at`（不再重复顶层字段）。

### 4.4 按住说话（语音）

- 方案：**Web Speech API**（Demo / 简历项目，零 ASR 云费用）。
- UI：豆包式单条输入框——左侧麦克风/键盘切换，中间输入或「按住 说话」，右侧发送。
- 按住识别，松手发送；按钮上只显示「按住 说话 / 松开发送」，**不把中间识别字盖在按钮上**。
- 需 Chrome + `localhost` 或 HTTPS；键盘输入始终可用作保底。

与豆包产品对比（选型说明）：

| | 豆包 App | 本项目 Demo |
|--|----------|-------------|
| 识别 | 自研云端 ASR（Seed-ASR），API 按量付费 | 浏览器 Web Speech |
| 成本 | 商用对接要花钱 | 基本免费 |
| 稳定性 | 高 | 依赖浏览器与网络 |

---

## 5. 后端接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/sessions` | 历史列表 |
| GET | `/sessions/{id}` | 会话详情 |
| POST | `/sessions` | 新建会话 |
| DELETE | `/sessions/{id}` | 删除会话 |
| POST | `/chat` | 流式聊天（SSE） |

开发时前端通过 Vite 将 `/api` 代理到 `http://127.0.0.1:8000`（SSE 关闭代理缓冲）。

---

## 6. 本地如何跑

### 后端

```bash
cd back
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 在 .env 中配置：DEEPSEEK_API_KEY=你的密钥
python main.py
```

### 前端

```bash
cd front
nvm use 20   # 需 Node >= 18
pnpm install # 若 PyPI/npm 慢可用国内镜像
pnpm dev
```

浏览器打开 `http://localhost:5173`。

常见问题：

- `externally-managed-environment`：用虚拟环境，勿往系统 Python 硬装包。
- pip 访问 pypi.org SSL 失败：换清华等国内镜像。
- `/chat` 500：多半未配置或未加载 `DEEPSEEK_API_KEY`，或后端未启动。
- `__pycache__`：Python 自动字节码缓存，可删，勿提交。

---

## 7. 后端模块拆分说明

原先单文件 `main.py` 过大，已按职责拆开：

- `config`：配置与常量  
- `schemas`：Pydantic 模型  
- `session_store`：会话文件  
- `llm`：大模型调用  
- `routers/*`：HTTP 路由  
- `main`：只负责组装 App  

启动方式不变：`python main.py`（`uvicorn.run("main:app", ...)`）。

---

## 8. 部署（摘要）

生产相关细节见 `docs/deploy.md`、`docs/server.md`。要点：

- 前端构建 `dist`，Nginx 托管静态资源并反代 `/api`。
- 后端用 systemd 常驻。
- 上线需 **HTTPS**（麦克风权限要求）。
- 密钥只放服务器环境 / `.env`，不要进 Git。

---

## 9. V1.0.0 范围与后续可选项

**已包含：** Vue 脚手架与暗色聊天页、会话 CRUD 与 JSON 落盘、DeepSeek 流式对话、思考中动画、按住说话（Web Speech）、后端模块化、部署模板。

**未强制包含（可后续迭代）：** 付费云 ASR、本地 Whisper/FunASR、多用户账号体系、会话列表服务端排序按 `updated_at` 等。

---

## 10. 版本

- 文档版本：V1.0.0  
- 对应能力：上述「已包含」功能集
