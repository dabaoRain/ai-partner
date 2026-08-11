import request from '@/utils/request'
import { useUserStore } from '@/store'

/**
 * 拉取历史会话列表（来自 sessions 目录，最新在前）
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
 * 删除会话文件
 * @param {string} sessionId
 */
export function deleteSession(sessionId) {
  return request({
    url: `/sessions/${sessionId}`,
    method: 'delete',
  })
}

/**
 * 流式发送聊天消息（SSE）
 * @param {{ message: string, name: string, personality: string, session_id: string, history?: Array<{role: string, content: string}> }} data
 * @param {{ onChunk?: (text: string) => void, onDone?: () => void, onError?: (err: Error) => void }} handlers
 */
export async function sendChatStream(data, handlers = {}) {
  const { onChunk, onDone, onError } = handlers
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
    })
  } catch (error) {
    const err = error instanceof Error ? error : new Error('网络异常')
    onError?.(err)
    throw err
  }

  if (!response.ok) {
    let detail = `请求失败(${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') {
        detail = body.detail
      }
    } catch {
      // ignore
    }
    const err = new Error(detail)
    onError?.(err)
    throw err
  }

  if (!response.body) {
    const err = new Error('浏览器不支持流式响应')
    onError?.(err)
    throw err
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

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
          onDone?.()
          return
        }

        let json
        try {
          json = JSON.parse(payload)
        } catch {
          continue
        }

        if (json.error) {
          const err = new Error(json.error)
          onError?.(err)
          throw err
        }

        if (json.content) {
          onChunk?.(json.content)
        }
      }
    }

    onDone?.()
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw error
    }
    const err = new Error('流式读取失败')
    onError?.(err)
    throw err
  }
}
