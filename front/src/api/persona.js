import request from '@/utils/request'

/** 官方人设列表（只读） */
export function fetchPersonas() {
  return request({
    url: '/personas',
    method: 'get',
  })
}

/** 默认人设（排序第一） */
export function fetchDefaultPersona() {
  return request({
    url: '/personas/default',
    method: 'get',
  })
}

/**
 * 单条官方人设
 * @param {string} id
 */
export function fetchPersona(id) {
  return request({
    url: `/personas/${id}`,
    method: 'get',
  })
}

/** 当前用户对某个人设的评价 */
export function fetchPersonaRating(id) {
  return request({
    url: `/personas/${id}/rating`,
    method: 'get',
  })
}

/** 提交/更新人设评价：1～5 分 + 备注 */
export function submitPersonaRating(id, data) {
  return request({
    url: `/personas/${id}/rating`,
    method: 'post',
    data,
  })
}
