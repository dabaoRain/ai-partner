import { onUnmounted, ref } from 'vue'

/**
 * 浏览器 Web Speech API 语音识别（前端独立，不经后端）
 * 建议在 HTTPS / localhost + Chrome 下使用
 */
export function useSpeechRecognition(options = {}) {
  const { lang = 'zh-CN' } = options

  const supported = ref(false)
  const listening = ref(false)

  let recognition = null
  let finalTranscript = ''
  let onInterim = null
  let onFinal = null
  let onError = null

  function getSpeechRecognition() {
    if (typeof window === 'undefined') return null
    return window.SpeechRecognition || window.webkitSpeechRecognition || null
  }

  supported.value = Boolean(getSpeechRecognition())

  function cleanupRecognition() {
    if (!recognition) return
    recognition.onstart = null
    recognition.onresult = null
    recognition.onerror = null
    recognition.onend = null
    try {
      recognition.abort()
    } catch {
      // ignore
    }
    recognition = null
  }

  /**
   * 开始识别
   * @param {{ onInterim?: (text: string) => void, onFinal?: (text: string) => void, onError?: (message: string) => void }} handlers
   */
  function start(handlers = {}) {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) {
      handlers.onError?.('当前浏览器不支持语音识别，请使用 Chrome')
      return false
    }
    if (listening.value) return true

    onInterim = handlers.onInterim || null
    onFinal = handlers.onFinal || null
    onError = handlers.onError || null
    finalTranscript = ''

    cleanupRecognition()
    recognition = new SpeechRecognition()
    recognition.lang = lang
    recognition.interimResults = true
    recognition.continuous = true

    recognition.onstart = () => {
      listening.value = true
    }

    recognition.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0]?.transcript || ''
        if (event.results[i].isFinal) {
          finalTranscript += piece
        } else {
          interim += piece
        }
      }
      onInterim?.(`${finalTranscript}${interim}`.trim())
    }

    recognition.onerror = (event) => {
      const errorType = event?.error || 'unknown'
      // aborted / no-speech 在松手场景较常见，不当作硬错误提示
      if (errorType === 'aborted' || errorType === 'no-speech') {
        return
      }
      if (errorType === 'not-allowed') {
        onError?.('请允许浏览器使用麦克风')
        return
      }
      if (errorType === 'network') {
        onError?.('语音识别网络异常，请检查网络后重试')
        return
      }
      onError?.(`语音识别失败: ${errorType}`)
    }

    recognition.onend = () => {
      listening.value = false
      const text = finalTranscript.trim()
      const finish = onFinal
      onInterim = null
      onFinal = null
      onError = null
      recognition = null
      finish?.(text)
    }

    try {
      recognition.start()
      return true
    } catch (error) {
      listening.value = false
      handlers.onError?.(error?.message || '无法启动语音识别')
      return false
    }
  }

  /** 结束识别，等待 onend 回调最终文本 */
  function stop() {
    if (!recognition) {
      listening.value = false
      return
    }
    try {
      recognition.stop()
    } catch {
      listening.value = false
      onFinal?.(finalTranscript.trim())
      cleanupRecognition()
    }
  }

  /** 取消识别，不触发业务发送 */
  function cancel() {
    onFinal = null
    onInterim = null
    finalTranscript = ''
    cleanupRecognition()
    listening.value = false
  }

  onUnmounted(() => {
    cancel()
  })

  return {
    supported,
    listening,
    start,
    stop,
    cancel,
  }
}
