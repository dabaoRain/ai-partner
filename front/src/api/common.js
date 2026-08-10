import request from '@/utils/request'

/** 健康检查示例接口 */
export function fetchHealth() {
  return request({
    url: '/health',
    method: 'get',
  })
}
