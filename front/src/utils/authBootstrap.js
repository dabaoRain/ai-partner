import { createGuest } from '@/api/auth'
import { useUserStore } from '@/store'

/**
 * 确保本地具备可用凭证：已登录则保留；否则签发/续期 Guest。
 */
export async function ensureAuthReady() {
  const userStore = useUserStore()
  if (userStore.accessToken) {
    return
  }
  const res = await createGuest(userStore.guestToken || undefined)
  userStore.setGuestToken(res.guest_token)
}
