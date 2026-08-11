import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_PREFIX || '/api',
  timeout: 30000,
})

service.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    const token = userStore.authToken
    if (token) {
      config.headers = config.headers || {}
      if (!config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    const message =
      (typeof detail === 'string' ? detail : null) ||
      error.response?.data?.message ||
      error.message ||
      '请求失败'

    // Access 失效时清登录态；保留 guest。claim/login 的 401 不误清用户会话
    if (status === 401) {
      const userStore = useUserStore()
      const url = String(error.config?.url || '')
      const skipClear =
        url.includes('/auth/claim-guest') ||
        url.includes('/auth/login') ||
        url.includes('/auth/register') ||
        url.includes('/auth/guest')
      if (userStore.accessToken && !skipClear) {
        userStore.clearUserSession()
      }
    }

    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default service
