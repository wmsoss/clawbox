<template>
  <div class="agent-config-panel">
    <!-- Agent 状态 & 控制 -->
    <div class="section">
      <div class="section-header">
        <el-icon><Monitor /></el-icon>
        <span>引擎状态</span>
      </div>
      <div class="status-row">
        <el-tag
          :type="statusTagType"
          size="large"
          effect="dark"
          round
        >
          {{ agentStore.status }}
        </el-tag>
        <div class="control-btns">
          <el-tooltip content="打开 OpenClaw Web UI" placement="top">
            <el-button
              type="primary"
              size="small"
              circle
              @click="openWebUI"
            >
              <el-icon><Link /></el-icon>
            </el-button>
          </el-tooltip>
          <el-button
            v-if="agentStore.status !== 'RUNNING'"
            type="success"
            size="small"
            :loading="agentStore.loading"
            @click="handleStart"
          >
            <el-icon><CaretRight /></el-icon>启动
          </el-button>
          <el-button
            v-if="agentStore.status === 'RUNNING'"
            type="danger"
            size="small"
            :loading="agentStore.loading"
            @click="handleStop"
          >
            <el-icon><VideoPause /></el-icon>停止
          </el-button>
        </div>
      </div>
    </div>

    <!-- 当前配置概览 -->
    <div class="section">
      <div class="section-header">
        <el-icon><Setting /></el-icon>
        <span>当前配置</span>
      </div>
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="Provider">
          {{ configProvider }}
        </el-descriptions-item>
        <el-descriptions-item label="Model">
          {{ configModel }}
        </el-descriptions-item>
        <el-descriptions-item label="Base URL">
          <span class="url-text">{{ configBaseUrl }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 资源监控 -->
    <div class="section">
      <div class="section-header">
        <el-icon><Cpu /></el-icon>
        <span>资源监控</span>
      </div>
      <div class="resource-grid">
        <div class="resource-item">
          <el-progress
            type="dashboard"
            :percentage="agentStore.resources.cpu_percent"
            :width="80"
            :stroke-width="6"
            :color="progressColor"
          />
          <span class="resource-label">CPU</span>
        </div>
        <div class="resource-item">
          <el-progress
            type="dashboard"
            :percentage="agentStore.resources.memory_percent"
            :width="80"
            :stroke-width="6"
            :color="progressColor"
          />
          <span class="resource-label">
            内存 ({{ agentStore.resources.memory_available_mb }}MB 可用)
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { useAgentStore } from '@/stores/agent'
import { ElMessage } from 'element-plus'
import { Monitor, Setting, CaretRight, VideoPause, Cpu, Link } from '@element-plus/icons-vue'

const agentStore = useAgentStore()

const statusTagType = computed(() => {
  switch (agentStore.status) {
    case 'RUNNING': return 'success'
    case 'STOPPED': return 'info'
    case 'STARTING': return 'warning'
    case 'FATAL': return 'danger'
    default: return 'info'
  }
})

const configProvider = computed(() => {
  try {
    const providers = agentStore.config?.models?.providers || {}
    return Object.keys(providers)[0] || '未配置'
  } catch { return '未配置' }
})

const configModel = computed(() => {
  try {
    return agentStore.config?.agents?.defaults?.model?.primary || '未配置'
  } catch { return '未配置' }
})

const configBaseUrl = computed(() => {
  try {
    const providers = agentStore.config?.models?.providers || {}
    const firstKey = Object.keys(providers)[0]
    return firstKey ? providers[firstKey].baseUrl || '-' : '-'
  } catch { return '-' }
})

const progressColor = [
  { color: '#67c23a', percentage: 50 },
  { color: '#e6a23c', percentage: 80 },
  { color: '#f56c6c', percentage: 100 }
]

let resourceTimer: ReturnType<typeof setInterval> | null = null

async function handleStart() {
  try {
    await agentStore.startAgent()
    ElMessage.success('引擎启动指令已发送')
    // 3 秒后刷新状态
    setTimeout(() => agentStore.fetchStatus(), 3000)
  } catch (e: any) {
    ElMessage.error('启动失败: ' + (e.message || e))
  }
}

async function handleStop() {
  try {
    await agentStore.stopAgent()
    ElMessage.success('引擎已停止')
  } catch (e: any) {
    ElMessage.error('停止失败: ' + (e.message || e))
  }
}

function openWebUI() {
  const host = window.location.hostname
  window.open(`http://${host}:18789/`, '_blank')
}

onMounted(() => {
  agentStore.fetchConfig()
  agentStore.fetchStatus()
  agentStore.fetchResources()
  // 每 5 秒轮询资源 + 状态
  resourceTimer = setInterval(() => {
    agentStore.fetchResources()
    agentStore.fetchStatus()
  }, 5000)
})

onBeforeUnmount(() => {
  if (resourceTimer) {
    clearInterval(resourceTimer)
    resourceTimer = null
  }
})
</script>

<style scoped>
.agent-config-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section {
  background: #fafbfc;
  border-radius: 8px;
  padding: 14px;
  border: 1px solid #ebeef5;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-btns {
  display: flex;
  gap: 8px;
}

.resource-grid {
  display: flex;
  justify-content: space-around;
  align-items: center;
}

.resource-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.resource-label {
  font-size: 12px;
  color: #909399;
}

.url-text {
  word-break: break-all;
  font-size: 12px;
  color: #909399;
}
</style>
