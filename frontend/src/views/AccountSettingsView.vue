<template>
  <div class="settings-container">
    <NavBar />

    <el-card class="settings-card">
      <h3 class="page-title">账户安全设置</h3>
      <p class="page-desc">修改登录密码</p>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px" class="settings-form">
        <el-form-item label="当前密码" prop="current_password">
          <el-input v-model="form.current_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password placeholder="请输入新密码（至少 6 位）" />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleChangePassword">保存新密码</el-button>
          <el-button @click="handleResetToDefault">重置为默认密码</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <h4>安全提示</h4>
      <ul class="security-tips">
        <li>密码长度至少 6 位</li>
        <li>建议定期更换密码</li>
        <li>忘记时可登录页点击「重置密码为默认值」</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import NavBar from '@/components/common/NavBar.vue'
import { apiFetch } from '@/utils/api'

const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPassword = (rule: any, value: string, callback: Function) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = reactive<FormRules>({
  current_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
})

async function handleChangePassword() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      // 先用当前密码尝试登录获取 token
      const loginParams = new URLSearchParams()
      loginParams.append('username', 'admin')
      loginParams.append('password', form.current_password)

      const loginRes = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: loginParams
      })

      if (!loginRes.ok) {
        throw new Error('当前密码错误')
      }

      // 用新密码重置
      await apiFetch('/api/v1/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify(form.new_password)
      })

      ElMessage.success('密码已修改，请使用新密码重新登录')

      // 清空表单
      form.current_password = ''
      form.new_password = ''
      form.confirm_password = ''
      formRef.value?.resetFields()

      // 退出登录
      setTimeout(() => {
        window.location.href = '/login'
      }, 1500)
    } catch (err: any) {
      ElMessage.error(err.message || '修改失败')
    } finally {
      saving.value = false
    }
  })
}

async function handleResetToDefault() {
  try {
    await ElMessageBox.confirm(
      '确定将密码重置为 12345678 吗？',
      '重置密码',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await apiFetch('/api/v1/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify('12345678')
    })

    ElMessage.success('密码已重置为 12345678')

    setTimeout(() => {
      window.location.href = '/login'
    }, 1500)
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.message || '重置失败')
    }
  }
}
</script>

<style scoped>
.settings-container {
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-card {
  max-width: 1200px;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #303133;
}

.page-desc {
  margin: 0 0 24px 0;
  color: #909399;
  font-size: 14px;
}

.settings-form {
  max-width: 600px;
}

.security-tips {
  margin: 16px 0 0 20px;
  padding: 0;
  color: #606266;
  font-size: 14px;
  line-height: 2;
}
</style>
