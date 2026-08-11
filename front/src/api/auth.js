import request from '@/utils/request'

export function createGuest(token) {
  const headers = {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return request({
    url: '/auth/guest',
    method: 'post',
    headers,
  })
}

export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data,
  })
}

export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data,
  })
}

export function refreshToken(refresh_token) {
  return request({
    url: '/auth/refresh',
    method: 'post',
    data: { refresh_token },
  })
}

export function logout(refresh_token) {
  return request({
    url: '/auth/logout',
    method: 'post',
    data: { refresh_token },
  })
}

export function fetchMe() {
  return request({
    url: '/auth/me',
    method: 'get',
  })
}

/**
 * 明确授权后合并匿名会话
 * @param {{ guest_token: string, consent: true }} data
 */
export function claimGuest(data) {
  return request({
    url: '/auth/claim-guest',
    method: 'post',
    data,
  })
}
