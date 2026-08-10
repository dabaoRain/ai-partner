# 请求/响应数据模型
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """单条对话消息，与 DeepSeek / OpenAI Chat Completions 的 messages 元素对齐。

    前端会话列表里存的每条 { role, content } 都会按此结构传入；
    后端组装大模型请求时也会原样展开进 messages 数组。
    """

    # 消息角色：user=用户，assistant=AI 伴侣；system 一般不由前端 history 传入，
    # 而是由后端根据 name/personality 单独生成。
    role: str
    # 该角色说出的文本内容；用户输入或模型历史回复都放在这里。
    content: str


class ChatRequest(BaseModel):
    """前端「发送消息」接口的入参，对应页面侧栏人设 + 当前会话上下文。

    数据流：HomeView.sendMessage → POST /chat → 本模型校验 → 拼成大模型 messages。
    """

    # 本轮用户刚输入的问题（必填）。对应原先脚本里写死的 user content，
    # 会作为 messages 的最后一条 {"role": "user", "content": message} 发给大模型。
    message: str = Field(..., min_length=1)
    # AI 伴侣名字（必填），来自左侧「名字」输入框；每轮请求动态传入，
    # 写入 system 提示词，不再使用后端写死的人设。
    name: str = Field(..., min_length=1)
    # AI 伴侣性格（必填），来自左侧「性格」文本框；与 name、message 一并传入，
    # 动态组成 system prompt，约束回复口吻。
    personality: str = Field(..., min_length=1)
    # 当前会话 ID（必填），由后端 POST /sessions 生成；前端仅回传，不自行造号。
    # 格式 年月日_时分秒，同时作为 sessions 目录下 JSON 文件名（不含扩展名）。
    session_id: str = Field(..., min_length=1)
    # 当前会话的历史消息（不含本轮 message）。用于多轮连续对话，让模型记得上文；
    # 前端应传 activeMessages 去掉最后一条用户消息后的列表，顺序为时间正序。
    history: list[ChatMessage] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    """新建会话入参：带上当前人设，后端生成 session_id 并创建空会话文件。"""

    name: str = Field(..., min_length=1)
    personality: str = Field(..., min_length=1)


class CreateSessionResponse(BaseModel):
    """新建会话出参：返回后端生成的会话 ID，供后续 /chat 使用。"""

    session_id: str


class SessionListItem(BaseModel):
    """历史会话列表项，对应 sessions 目录下的一个 JSON 文件。"""

    session_id: str
    name: str
    personality: str
    created_at: str = ""
    updated_at: str = ""


class SessionDetailResponse(BaseModel):
    """会话详情：含人设与可直接渲染的 messages。"""

    session_id: str
    name: str
    personality: str
    created_at: str = ""
    updated_at: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """非流式聊天出参（当前 /chat 为 SSE，保留模型便于扩展）。"""

    # DeepSeek 返回的 assistant 文本。
    content: str
