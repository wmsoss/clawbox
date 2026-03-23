<template>
  <div class="dashboard-container">
    <!-- Shared Navigation Bar -->
    <NavBar />

    <el-card class="box-card mb-4">
      <!-- Layout as per §7.2 specification -->
      <div class="layout-grid">
        <!-- Left Panel: 350px 固定 -->
        <div class="panel-left">
          <!-- Agent 配置 & 资源监控 -->
          <div class="left-section left-config">
            <AgentConfig />
          </div>

          <!-- Monaco 编辑器 -->
          <div class="left-section left-editor">
            <MonacoEditor />
          </div>
        </div>

        <!-- Right Panel: noVNC and Xterm -->
        <div class="panel-right">
          <div class="novnc-section">
            <div class="section-title-row">
              <h4 class="section-title">远程可视化桌面 (noVNC)</h4>
              <el-tooltip content="在新标签页打开全屏 noVNC" placement="top">
                <el-button size="small" circle @click="openVncFullscreen">
                  <el-icon><FullScreen /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
            <NoVNCViewer />
          </div>

          <div class="xterm-section">
            <div class="section-title-row">
              <h4 class="section-title">引擎日志及交互 (Xterm.js)</h4>
              <el-tooltip content="打开全屏终端" placement="top">
                <el-button size="small" circle @click="openTerminalFullscreen">
                  <el-icon><FullScreen /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
            <XtermLog />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { FullScreen } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import NoVNCViewer from '@/components/dashboard/NoVNCViewer.vue'
import XtermLog from '@/components/dashboard/XtermLog.vue'
import AgentConfig from '@/components/dashboard/AgentConfig.vue'
import MonacoEditor from '@/components/dashboard/MonacoEditor.vue'
import NavBar from '@/components/common/NavBar.vue'

const router = useRouter()

function openVncFullscreen() {
  const host = window.location.hostname
  window.open(`http://${host}:6080/vnc.html?autoconnect=true&resize=remote`, '_blank')
}

function openTerminalFullscreen() {
  router.push('/terminal')
}
</script>

<style scoped>
.dashboard-container {
  padding: 1rem;
  max-width: 1600px;
  margin: 0 auto;
}

.box-card {
  height: calc(100vh - 5rem);
  display: flex;
  flex-direction: column;
}

/* Flex grow the body to fill the card */
:deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 1rem;
}

.layout-grid {
  display: flex;
  gap: 1rem;
  height: 100%;
}

/* Left Panel: Fixed width per §7.2 (350px) */
.panel-left {
  flex: 0 0 350px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.left-section {
  flex-shrink: 0;
}

.left-editor {
  flex: 1;
  min-height: 320px;
  display: flex;
  flex-direction: column;
}

/* Right Panel: Flexible width */
.panel-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.section-title {
  margin: 0;
  font-size: 14px;
  color: #606266;
}

.novnc-section {
  flex: 0 0 60%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.xterm-section {
  flex: 0 0 calc(40% - 1rem);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

:deep(.novnc-container) {
  flex: 1;
}

:deep(.xterm-container) {
  flex: 1;
}
</style>
