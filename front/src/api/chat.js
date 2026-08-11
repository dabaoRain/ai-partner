import request from '@/utils/request'
import { useUserStore } from '@/store'
import { ChatStreamError, toChatStreamError } from '@/utils/chatError'

/**
 * 拉取历史会话列表
 */
export function fetchSessions() {
  return request({
    url: '/sessions',
    method: 'get',
  })
}

/**
 * 拉取单个会话详情（含 messages）
 * @param {string} sessionId
 */
export function fetchSessionDetail(sessionId) {
  return request({
    url: `/sessions/${sessionId}`,
    method: 'get',
  })
}

/**
 * 新建会话（session_id 由后端生成）
 * @param {{ name: string, personality: string }} data
 */
export function createSession(data) {
  return request({
    url: '/sessions',
    method: 'post',
    data,
  })
}

/**
 * 删除会话
 * @param {string} sessionId
 */
export function deleteSession(sessionId) {
  return request({
    url: `/sessions/${sessionId}`,
    method: 'delete',
  })
}

/**
 * 请求服务端停止生成（不走 axios，避免完成后 404 弹全局错误）
 * @param {string} clientRequestId
 */
export async function stopChat(clientRequestId) {
  const prefix = import.meta.env.VITE_API_PREFIX || '/api'
  const userStore = useUserStore()
  const headers = { 'Content-Type': 'application/json' }
  if (userStore.authToken) {
    headers.Authorization = `Bearer ${userStore.authToken}`
  }
  const response = await fetch(`${prefix}/chat/stop`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ client_request_id: clientRequestId }),
  })
  if (!response.ok && response.status !== 404) {
    throw new Error(`停止失败(${response.status})`)
  }
  return response.json().catch(() => ({ ok: true }))
}

/**
 * 流式发送聊天消息（SSE）
 * @param {{
 *   message: string,
 *   name: string,
 *   personality: string,
 *   session_id: string,
 *   client_request_id: string,
 *   history?: Array<{role: string, content: string}>
 * }} data
 * @param {{
 *   signal?: AbortSignal,
 *   onChunk?: (text: string) => void,
 *   onStart?: (meta: { client_request_id?: string }) => void,
 *   onDone?: () => void,
 *   onError?: (err: ChatStreamError) => void
 * }} handlers
 */
export async function sendChatStream(data, handlers = {}) {
  const { signal, onChunk, onStart, onDone, onError } = handlers
  const prefix = import.meta.env.VITE_API_PREFIX || '/api'

  const userStore = useUserStore()
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (userStore.authToken) {
    headers.Authorization = `Bearer ${userStore.authToken}`
  }

  let response
  try {
    response = await fetch(`${prefix}/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      const err = new ChatStreamError('CLIENT_CANCELLED', '已停止生成', false)
      onError?.(err)
      throw err
    }
    const err = toChatStreamError(null, '网络异常')
    err.code = 'NETWORK_ERROR'
    err.retryable = true
    onError?.(err)
    throw err
  }

  if (!response.ok) {
    let detail = `请求失败(${response.status})`
    let parsed = null
    try {
      const body = await response.json()
      parsed = body?.detail
      if (typeof parsed === 'string') {
        detail = parsed
      } else if (parsed && typeof parsed === 'object' && parsed.message) {
        detail = parsed.message
      }
    } catch {
      // ignore
    }
    const err = toChatStreamError(parsed, detail)
    if (response.status === 409) {
      err.retryable = false
    }
    onError?.(err)
    throw err
  }

  if (!response.body) {
    const err = new ChatStreamError('UNSUPPORTED', '浏览器不支持流式响应', false)
    onError?.(err)
    throw err
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let settled = false

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''

      for (const part of parts) {
        const line = part
          .split('\n')
          .map((item) => item.trim())
          .find((item) => item.startsWith('data:'))
        if (!line) continue

        const payload = line.slice(5).trim()
        if (payload === '[DONE]') {
          settled = true
          onDone?.()
          return
        }

        let json
        try {
          json = JSON.parse(payload)
        } catch {
          continue
        }

        if (json.event === 'start') {
          onStart?.(json)
          continue
        }

        if (json.error) {
          const err = toChatStreamError(json.error, '流式回复失败')
          settled = true
          onError?.(err)
          throw err
        }

        if (json.content) {
          onChunk?.(json.content)
        }
      }
    }

    if (!settled) {
      // 连接正常结束但未收到 DONE：视为断流
      const err = new ChatStreamError(
        'STREAM_INTERRUPTED',
        '连接中断，请重试',
        true,
      )
      onError?.(err)
      throw err
    }
    onDone?.()
  } catch (error) {
    if (error instanceof ChatStreamError) {
      throw error
    }
    if (error?.name === 'AbortError') {
      const err = new ChatStreamError('CLIENT_CANCELLED', '已停止生成', false)
      onError?.(err)
      throw err
    }
    const err = new ChatStreamError('STREAM_INTERRUPTED', '流式读取失败', true)
    onError?.(err)
    throw err
  }
}
