<template>
  <div class="terminal-view">
    <div class="terminal-header">
      <div class="header-left">
        <span class="terminal-title">🦞 大龙虾终端</span>
      </div>
      <div class="header-right">
        <el-button size="small" @click="goBack">
          <el-icon><Back /></el-icon>返回主控台
        </el-button>
      </div>
    </div>
    <div class="terminal-body">
      <XtermLog />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Back } from '@element-plus/icons-vue'
import XtermLog from '@/components/dashboard/XtermLog.vue'

const router = useRouter()

function goBack() {
  router.push('/dashboard')
}
</script>

<style scoped>
.terminal-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #2d2d2d;
  border-bottom: 1px solid #404040;
  flex-shrink: 0;
}

.terminal-title {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
}

.terminal-body {
  flex: 1;
  min-height: 0;
}
</style>
