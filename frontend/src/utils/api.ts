// frontend/src/utils/api.ts
// 极简 Fetch 封装，自动注入 JWT Token
import { useAuthStore } from '@/stores/auth'

export async function apiFetch(endpoint: string, options: RequestInit = {}) {
  const authStore = useAuthStore()
  
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  
  if (authStore.token) {
    headers.set('Authorization', `Bearer ${authStore.token}`)
  }

  const response = await fetch(endpoint, {
    ...options,
    headers
  })

  if (!response.ok) {
    const errText = await response.text()
    throw new Error(`API Error ${response.status}: ${errText}`)
  }

  return response.json()
}
