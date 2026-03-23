<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>🦞 大龙虾引擎</h2>
          <p class="subtitle">请登录管理员账号</p>
        </div>
      </template>

      <el-form
        :model="form"
        :rules="rules"
        ref="formRef"
        label-width="80px"
        class="login-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="管理员用户名" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="管理员密码"
            @keyup.enter="submitLogin"
          />
        </el-form-item>

        <div class="actions">
          <el-button type="primary" :loading="loading" @click="submitLogin" style="width: 100%">
            登录
          </el-button>
        </div>
        
        <div class="reset-link-container">
          <el-link type="warning" :underline="false" @click="handleResetSystem">
            忘记密码？重置系统
          </el-link>
          <span class="divider">|</span>
          <el-link type="primary" :underline="false" @click="handleResetPassword">
            重置密码为默认值
          </el-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSetupStore } from '@/stores/setup'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
})

async function submitLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const params = new URLSearchParams()
      params.append('username', form.username)
      params.append('password', form.password)

      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params
      })

      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || '登录验证失败')
      }

      auth.setToken(data.access_token)
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } catch (err: any) {
      ElMessage.error(err.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}

async function handleResetSystem() {
  try {
    const { value } = await ElMessageBox.prompt(
      '此操作将清空所有管理员账号和系统向导状态，重新回到初始化流程。<br/><br/>已安装的技能和配置文件将被保留。<br/><br/>请在下方输入 <b>RESET</b> 以确认该操作：',
      '⚠️ 重置系统警告',
      {
        confirmButtonText: '确定重置',
        cancelButtonText: '取消',
        inputPattern: /^RESET$/,
        inputErrorMessage: '输入不匹配，请确切输入全大写的 RESET',
        type: 'warning',
        dangerouslyUseHTMLString: true,
        confirmButtonClass: 'el-button--danger'
      }
    )

    if (value === 'RESET') {
      const res = await fetch('/api/v1/auth/reset-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: 'RESET' })
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || '系统重置失败')
      }

      ElMessage.success('系统已重置，即将返回初始向导流程')

      // Clear stores and navigate to wizard
      auth.clearToken()
      const setupStore = useSetupStore()
      setupStore.reset()

      router.push('/wizard')
    }
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.message || '操作失败')
    }
  }
}

async function handleResetPassword() {
  try {
    const { value: username } = await ElMessageBox.prompt(
      '请输入要重置密码的用户名：',
      '重置密码',
      {
        confirmButtonText: '确定重置',
        cancelButtonText: '取消',
        inputPattern: /.+/,
        inputErrorMessage: '用户名不能为空',
        type: 'info'
      }
    )

    const { value: confirm } = await ElMessageBox.confirm(
      `确定将用户 "${username}" 的密码重置为 12345678 吗？`,
      '确认重置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (confirm) {
      const res = await fetch('/api/v1/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username,
          new_password: '12345678'
        })
      })

      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || '密码重置失败')
      }

      ElMessage.success(data.message || '密码已重置为 12345678')
    }
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.message || '操作失败')
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 100%;
  max-width: 420px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 4px 0;
  font-size: 24px;
}

.subtitle {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.login-form {
  padding-top: 1rem;
}

.actions {
  margin-top: 1.5rem;
}

.reset-link-container {
  margin-top: 1rem;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
}

.divider {
  color: #dcdfe6;
}
</style>
