// frontend/src/stores/auth.ts
// 鉴权状态管理 (使用 sessionStorage 持久化 token)
// sessionStorage: 刷新不丢失，关闭标签页后需重新登录
import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'dalongxia_auth_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(sessionStorage.getItem(STORAGE_KEY))

  function setToken(newToken: string) {
    token.value = newToken
    sessionStorage.setItem(STORAGE_KEY, newToken)
  }

  function clearToken() {
    token.value = null
    sessionStorage.removeItem(STORAGE_KEY)
  }

  return { token, setToken, clearToken }
})
