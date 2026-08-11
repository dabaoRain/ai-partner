import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const ACCESS_KEY = 'ai_partner_access_token'
const REFRESH_KEY = 'ai_partner_refresh_token'
const GUEST_KEY = 'ai_partner_guest_token'
const USER_KEY = 'ai_partner_user'

function readJSON(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const accessToken = ref(localStorage.getItem(ACCESS_KEY) || '')
  const refreshToken = ref(localStorage.getItem(REFRESH_KEY) || '')
  const guestToken = ref(localStorage.getItem(GUEST_KEY) || '')
  const userInfo = ref(readJSON(USER_KEY))

  const isLoggedIn = computed(() => Boolean(accessToken.value && userInfo.value))

  /** 业务请求优先用登录 Access，否则用 Guest */
  const authToken = computed(() => accessToken.value || guestToken.value || '')

  function setGuestToken(token) {
    guestToken.value = token || ''
    if (token) {
      localStorage.setItem(GUEST_KEY, token)
    } else {
      localStorage.removeItem(GUEST_KEY)
    }
  }

  function setAuthTokens({ access_token, refresh_token, user }) {
    accessToken.value = access_token || ''
    refreshToken.value = refresh_token || ''
    userInfo.value = user || null
    if (access_token) {
      localStorage.setItem(ACCESS_KEY, access_token)
    } else {
      localStorage.removeItem(ACCESS_KEY)
    }
    if (refresh_token) {
      localStorage.setItem(REFRESH_KEY, refresh_token)
    } else {
      localStorage.removeItem(REFRESH_KEY)
    }
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    } else {
      localStorage.removeItem(USER_KEY)
    }
  }

  function clearUserSession() {
    accessToken.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  }

  function logout() {
    clearUserSession()
  }

  return {
    accessToken,
    refreshToken,
    guestToken,
    userInfo,
    isLoggedIn,
    authToken,
    setGuestToken,
    setAuthTokens,
    clearUserSession,
    logout,
  }
})
