import request from '@/utils/request'

export function fetchPrivacyPolicy() {
  return request({
    url: '/privacy/policy',
    method: 'get',
  })
}

export function fetchPreferences() {
  return request({
    url: '/privacy/preferences',
    method: 'get',
  })
}

export function updatePreferences(data) {
  return request({
    url: '/privacy/preferences',
    method: 'patch',
    data,
  })
}

export function fetchMyPermissions() {
  return request({
    url: '/privacy/permissions',
    method: 'get',
  })
}

export function deleteAccount(password) {
  return request({
    url: '/auth/account',
    method: 'delete',
    data: { password },
  })
}
