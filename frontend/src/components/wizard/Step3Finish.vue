<template>
  <div class="step-container text-center">
    <el-result
      icon="success"
      title="配置就绪"
      sub-title="您已完成所有基本配置。点击下方按钮启动大龙虾引擎！"
    >
      <template #extra>
        <el-button @click="goBack">返回修改</el-button>
        <el-button type="success" :loading="starting" @click="finishSetup">
          启动引擎进入主控台
        </el-button>
      </template>
    </el-result>

    <div v-if="setup.configData.llm" class="summary-box">
      <strong>已选模型：</strong> {{ setup.configData.llm.model_name }}
      ({{ setup.configData.llm.provider }})
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSetupStore } from '@/stores/setup'
import { ElMessage } from 'element-plus'
import { apiFetch } from '@/utils/api'

const router = useRouter()
const setup = useSetupStore()
const starting = ref(false)

function goBack() {
  router.push({ query: { step: 2 } })
}

async function finishSetup() {
  starting.value = true

  try {
    // Step 1: 提交网络配置（如果有订阅链接）
    if (setup.configData.network?.subscription_url) {
      await apiFetch('/api/v1/network/apply', {
        method: 'POST',
        body: JSON.stringify({
          subscriptionUrl: setup.configData.network.subscription_url,
          useChinaDirect: true
        })
      })
    }

    // Step 2: 提交 LLM 配置到 config_builder → openclaw.json
    if (setup.configData.llm) {
      await apiFetch('/api/v1/llm/apply', {
        method: 'POST',
        body: JSON.stringify({
          provider: setup.configData.llm.provider,
          model_name: setup.configData.llm.model_name,
          api_key: setup.configData.llm.api_key,
          custom_base_url: setup.configData.llm.custom_base_url || '',
        })
      })
    }

    // Step 3: 启动 Agent
    await apiFetch('/api/v1/agent/start', { method: 'POST' })

    ElMessage.success('初装向导完毕！引擎正在启动…')

    // Mark setup as completed (userExists = true)
    setup.complete()

    // 直接进入 dashboard（Step0 已拿到 token，自动登录）
    router.push('/dashboard')
  } catch (err: any) {
    ElMessage.error('配置提交失败：' + (err.message || err))
  } finally {
    starting.value = false
  }
}
</script>

<style scoped>
.step-container {
  max-width: 600px;
  margin: 0 auto;
  padding-top: 2rem;
}
.text-center {
  text-align: center;
}
.summary-box {
  margin-top: 2rem;
  padding: 1rem;
  background-color: #f0f9eb;
  color: #67c23a;
  border-radius: 4px;
}
</style>
