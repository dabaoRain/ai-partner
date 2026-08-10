import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_PREFIX || '/api',
  timeout: 30000,
})

service.interceptors.request.use(
  (config) => {
    // 如需鉴权，可在此注入 token
    return config
  },
  (error) => Promise.reject(error)
)

service.interceptors.response.use(
  (response) => {
    const res = response.data
    // 按后端约定调整：默认认为直接返回业务数据
    return res
  },
  (error) => {
    const detail = error.response?.data?.detail
    const message =
      (typeof detail === 'string' ? detail : null) ||
      error.response?.data?.message ||
      error.message ||
      '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default service
