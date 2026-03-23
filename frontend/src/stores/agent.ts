// frontend/src/stores/agent.ts
// Agent 运行状态管理 (Pinia) — 白皮书 §7.2 Dashboard 支撑
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiFetch } from '@/utils/api'

export interface ResourceInfo {
  cpu_percent: number
  memory_percent: number
  memory_available_mb: number
}

export const useAgentStore = defineStore('agent', () => {
  const status = ref<string>('UNKNOWN')
  const config = ref<Record<string, any> | null>(null)
  const configRaw = ref<string>('')
  const resources = ref<ResourceInfo>({ cpu_percent: 0, memory_percent: 0, memory_available_mb: 0 })
  const loading = ref(false)

  async function fetchConfig() {
    try {
      const data = await apiFetch('/api/v1/agent/config')
      config.value = data
      configRaw.value = JSON.stringify(data, null, 2)
    } catch {
      config.value = null
      configRaw.value = ''
    }
  }

  async function saveConfig(jsonStr: string) {
    const parsed = JSON.parse(jsonStr) // throws if invalid json
    await apiFetch('/api/v1/agent/config', {
      method: 'PUT',
      body: JSON.stringify(parsed)
    })
    config.value = parsed
    configRaw.value = jsonStr
  }

  async function fetchStatus() {
    try {
      const data = await apiFetch('/api/v1/agent/status')
      status.value = data.status || 'UNKNOWN'
    } catch {
      status.value = 'UNKNOWN'
    }
  }

  async function startAgent() {
    loading.value = true
    try {
      await apiFetch('/api/v1/agent/start', { method: 'POST' })
      status.value = 'STARTING'
    } finally {
      loading.value = false
    }
  }

  async function stopAgent() {
    loading.value = true
    try {
      await apiFetch('/api/v1/agent/stop', { method: 'POST' })
      status.value = 'STOPPED'
    } finally {
      loading.value = false
    }
  }

  async function fetchResources() {
    try {
      const data = await apiFetch('/api/v1/agent/resources')
      resources.value = data
    } catch {
      // silently ignore polling failure
    }
  }

  return {
    status, config, configRaw, resources, loading,
    fetchConfig, saveConfig, fetchStatus, startAgent, stopAgent, fetchResources
  }
})
