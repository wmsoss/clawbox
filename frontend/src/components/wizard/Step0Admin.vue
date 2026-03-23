<template>
  <el-form :model="form" :rules="rules" ref="formRef" label-width="120px" class="step-form">
    <h3>初始管理员注册 / 登录</h3>
    <p class="desc">大龙虾采用单用户管理机制，首次运行需要设置管理员账号密码。</p>
    
    <el-form-item label="用户名" prop="username">
      <el-input v-model="form.username" placeholder="至少包含3个字符" />
    </el-form-item>
    
    <el-form-item label="密码" prop="password">
      <el-input v-model="form.password" type="password" show-password placeholder="至少包含8个字符" />
    </el-form-item>

    <div class="actions">
      <el-button type="primary" :loading="loading" @click="submitAuth">下一步</el-button>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['next'])
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: ''
})

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '长度在 3 到 32 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' }
  ]
})

async function submitAuth() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 尝试注册（若已有用户则后端返回 409）
        const regRes = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form)
        });
        
        if (!regRes.ok && regRes.status !== 409) {
          const errData = await regRes.json().catch(() => ({}));
          throw new Error(errData.detail || '注册请求失败');
        }

        // 调用登录接口获取真实 JWT
        const params = new URLSearchParams();
        params.append('username', form.username);
        params.append('password', form.password);

        const loginRes = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params
        });

        const loginData = await loginRes.json().catch(() => ({}));
        if (!loginRes.ok) {
          throw new Error(loginData.detail || '登录验证失败');
        }

        auth.setToken(loginData.access_token);
        ElMessage.success('管理员验证成功');
        emit('next');
      } catch (err: any) {
        ElMessage.error(err.message || '操作失败');
      } finally {
        loading.value = false;
      }
    }
  })
}
</script>

<style scoped>
.step-form {
  max-width: 500px;
  margin: 0 auto;
}
.desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 2rem;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 2rem;
}
</style>
