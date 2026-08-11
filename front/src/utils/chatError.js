/** 聊天流错误：携带后端错误码与是否可重试 */

export class ChatStreamError extends Error {
  /**
   * @param {string} code
   * @param {string} message
   * @param {boolean} retryable
   */
  constructor(code, message, retryable = false) {
    super(message || code)
    this.name = 'ChatStreamError'
    this.code = code || 'UNKNOWN'
    this.retryable = Boolean(retryable)
  }
}

/**
 * 从接口 detail / SSE error 解析为 ChatStreamError
 * @param {unknown} raw
 * @param {string} fallbackMessage
 */
export function toChatStreamError(raw, fallbackMessage = '请求失败') {
  if (raw instanceof ChatStreamError) return raw

  if (raw && typeof raw === 'object') {
    const obj = raw
    if (typeof obj.code === 'string') {
      return new ChatStreamError(
        obj.code,
        typeof obj.message === 'string' ? obj.message : fallbackMessage,
        Boolean(obj.retryable),
      )
    }
  }

  if (typeof raw === 'string') {
    return new ChatStreamError('HTTP_ERROR', raw, true)
  }

  return new ChatStreamError('UNKNOWN', fallbackMessage, true)
}
