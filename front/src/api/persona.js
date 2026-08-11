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
