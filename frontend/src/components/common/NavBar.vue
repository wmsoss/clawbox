<template>
  <div class="top-nav">
    <div class="nav-brand">🦞 大龙虾主控台</div>
    <div class="nav-links">
      <router-link to="/dashboard" class="nav-link" active-class="active">主控台</router-link>
      <a href="http://127.0.0.1:18789/" target="_blank" class="nav-link">OpenClaw 控制台</a>
      <router-link to="/settings/llm" class="nav-link" active-class="active">LLM 配置</router-link>
      <router-link to="/settings/openclaw" class="nav-link" active-class="active">OpenClaw 配置</router-link>
      <router-link to="/settings/account" class="nav-link" active-class="active">账户设置</router-link>
      <router-link to="/skills" class="nav-link" active-class="active">技能商店</router-link>
      <router-link to="/terminal" class="nav-link" active-class="active">终端</router-link>
    </div>
    <div class="nav-actions">
      <el-button size="small" @click="handleLogout">退出</el-button>
      <el-button type="danger" size="small" @click="handleReset">重置</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useSetupStore } from '@/stores/setup'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { apiFetch } from '@/utils/api'

const auth = useAuthStore()
const setup = useSetupStore()
const router = useRouter()

/** 退出：仅清除 session，跳转登录页 */
function handleLogout() {
  auth.clearToken()
  router.push('/login')
}

/** 重置：删除后端管理员 → 清除 session → 跳转向导 */
async function handleReset() {
  try {
    await ElMessageBox.confirm(
      '此操作将删除管理员账号并重置系统，需要重新走向导流程。确定重置？',
      '系统重置',
      { confirmButtonText: '确定重置', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await apiFetch('/api/v1/system/reset', { method: 'POST' })
  } catch (err: any) {
    console.warn('Reset API failed (proceeding with local cleanup):', err.message)
  }
  auth.clearToken()
  setup.reset()
  router.push('/wizard')
}
</script>

<style scoped>
.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 14px;
  color: #606266;
  text-decoration: none;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #f0f2f5;
  color: #409eff;
}

.nav-link.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}

.nav-actions {
  display: flex;
  gap: 8px;
}
</style>
