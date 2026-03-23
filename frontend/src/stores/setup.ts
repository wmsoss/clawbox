// frontend/src/stores/setup.ts
// 安装向导状态管理
// userExists 由 /api/v1/auth/check-user-exists 决定，用于路由守卫判断
import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'

export const useSetupStore = defineStore('setup', () => {
  const userExists = ref(false)
  const isLoaded = ref(false)

  // 临时存储各步骤的数据 payload，方便最后统一提交或步骤间回显
  const configData = reactive({
    network: null as any,
    llm: null as any
  })

  // 从后端 API 拉取 AdminUser 是否存在
  async function fetchState() {
    if (isLoaded.value) return
    try {
      const res = await fetch('/api/v1/auth/check-user-exists')
      if (res.ok) {
        const data = await res.json()
        userExists.value = !!data.exists
      }
    } catch (e) {
      console.error('Failed to check user existence:', e)
    } finally {
      isLoaded.value = true
    }
  }

  // 向导完成后调用
  function complete() {
    userExists.value = true
  }

  // 重置所有状态（退出并重置时调用）
  function reset() {
    userExists.value = false
    isLoaded.value = false
    configData.network = null
    configData.llm = null
  }

  return { userExists, isLoaded, configData, fetchState, complete, reset }
})
