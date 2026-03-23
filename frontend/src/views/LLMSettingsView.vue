<template>
  <div class="settings-container">
    <!-- Shared Navigation Bar -->
    <NavBar />

    <el-card class="settings-card">
      <h3 class="page-title">大模型 (LLM) 配置管理</h3>
      <p class="page-desc">修改驱动模型配置后，需重启引擎才能生效。</p>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px" class="settings-form">
        <el-form-item label="提供商" prop="provider">
          <el-select v-model="form.provider" @change="handleProviderChange" placeholder="选择服务商">
            <el-option label="阿里云百炼 (Coding Plan)" value="bailian" />
            <el-option label="DeepSeek 官方" value="deepseek" />
            <el-option label="OpenAI API" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="Google Gemini" value="gemini" />
            <el-option label="自定义 (Custom)" value="custom" />
          </el-select>
        </el-form-item>

        <!-- Base URL: bailian 只读展示, custom 可编辑, 其他大厂隐藏 -->
        <el-form-item v-if="form.provider === 'bailian'" label="Base URL">
          <el-input :model-value="form.custom_base_url" disabled />
        </el-form-item>

        <el-form-item v-if="form.provider === 'custom'" label="Base URL" prop="custom_base_url">
          <el-input v-model="form.custom_base_url" placeholder="https://api.example.com/v1" />
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
          <div style="display: flex; align-items: center; width: 100%; margin-top: 8px;">
            <el-button
              v-if="form.provider !== 'bailian' && form.provider !== 'custom'"
              size="small"
              @click="fetchModels"
              :loading="loadingModels"
              :disabled="!form.api_key"
            >
              获取模型列表
            </el-button>
            <span v-if="fetchError" class="fetch-error">自动获取失败，请手动输入模型 ID</span>
          </div>
        </el-form-item>

        <el-form-item label="驱动模型" prop="model_name">
          <el-select 
            v-model="form.model_name" 
            placeholder="选择或输入驱动模型" 
            :loading="loadingModels"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
          >
            <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
          <el-button @click="loadConfig">重新加载</el-button>
        </el-form-item>
      </el-form>

      <!-- 当前生效配置概览 -->
      <el-divider />
      <h4>当前生效配置 (openclaw.json)</h4>
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="Primary Model">{{ currentPrimary }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useAgentStore } from '@/stores/agent'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { apiFetch } from '@/utils/api'
import NavBar from '@/components/common/NavBar.vue'

const agentStore = useAgentStore()
const formRef = ref<FormInstance>()
const loadingModels = ref(false)
const fetchError = ref(false)
const saving = ref(false)

const PRESET_MODELS: Record<string, string[]> = {
  bailian: ['qwen3.5-plus', 'qwen3-max-2026-01-23', 'qwen3-coder-next', 'qwen3-coder-plus', 'glm-5', 'glm-4.7', 'kimi-k2.5', 'MiniMax-M2.5'],
}

const PRESET_BASE_URLS: Record<string, string> = {
  bailian: '',  // 百炼不预填，用户选择标准版或 Coding Plan
  deepseek: 'https://api.deepseek.com',
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com/v1',
  gemini: 'https://generativelanguage.googleapis.com/v1beta',
}

const form = reactive({
  provider: 'bailian',
  model_name: '',
  api_key: '',
  custom_base_url: ''
})

const availableModels = ref<string[]>([])

const rules = reactive<FormRules>({
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  api_key: [{ required: true, message: 'API Key 不能为空', trigger: 'blur' }],
  model_name: [{ required: true, message: '请选择驱动模型', trigger: 'change' }],
  custom_base_url: [{
    validator: (_rule: any, value: any, callback: any) => {
      if (form.provider === 'custom' && !value) {
        callback(new Error('请输入 Base URL'))
      } else {
        callback()
      }
    }, trigger: 'blur'
  }]
})

const currentPrimary = computed(() => {
  try {
    return agentStore.config?.agents?.defaults?.model?.primary || '未配置'
  } catch { return '未配置' }
})

function handleProviderChange(val: string) {
  form.model_name = ''
  fetchError.value = false
  availableModels.value = []

  if (val === 'bailian') {
    form.custom_base_url = PRESET_BASE_URLS.bailian!
  } else if (val === 'custom') {
    form.custom_base_url = ''
  } else {
    form.custom_base_url = PRESET_BASE_URLS[val] || ''
  }

  if (val === 'bailian') {
    availableModels.value = [...(PRESET_MODELS.bailian || [])]
    if (availableModels.value.length > 0) {
      form.model_name = availableModels.value[0]!
    }
  }
}

async function fetchModels() {
  if (!form.api_key) return
  loadingModels.value = true
  fetchError.value = false
  try {
    const params = new URLSearchParams()
    params.append('provider', form.provider)
    params.append('api_key', form.api_key)
    if (form.custom_base_url) {
      params.append('base_url', form.custom_base_url)
    }
    const res = await apiFetch(`/api/v1/llm/models?${params.toString()}`)
    const models = res.models || []
    if (models.length > 0) {
      availableModels.value = models
      if (!models.includes(form.model_name)) {
        form.model_name = models[0]
      }
      ElMessage.success(`成功拉取 ${models.length} 个可用模型`)
    } else {
      throw new Error('未获取到模型列表')
    }
  } catch {
    fetchError.value = true
  } finally {
    loadingModels.value = false
  }
}

async function saveConfig() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await apiFetch('/api/v1/llm/apply', {
        method: 'POST',
        body: JSON.stringify({
          provider: form.provider,
          model_name: form.model_name,
          api_key: form.api_key,
          custom_base_url: form.custom_base_url || '',
        })
      })
      ElMessage.success('LLM 配置已保存，请重启引擎使配置生效')
      await agentStore.fetchConfig()
    } catch (err: any) {
      ElMessage.error('配置保存失败：' + (err.message || err))
    } finally {
      saving.value = false
    }
  })
}

function loadConfig() {
  agentStore.fetchConfig()
  ElMessage.info('已重新加载配置')
}



onMounted(() => {
  agentStore.fetchConfig()
  handleProviderChange('bailian')
})
</script>

<style scoped>
.settings-container {
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* Top Navigation Bar - same as DashboardView */
.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.nav-brand {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.nav-links {
  display: flex;
  gap: 1rem;
}

.nav-link {
  font-size: 14px;
  color: var(--el-text-color-regular);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 4px;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #f5f7fa;
  color: var(--el-color-primary);
}

.nav-link.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 500;
}

.settings-card {
  max-width: 700px;
}

.page-title {
  margin: 0 0 4px 0;
  font-size: 18px;
}

.page-desc {
  color: #909399;
  font-size: 14px;
  margin: 0 0 1.5rem 0;
}

.settings-form {
  max-width: 550px;
}

.fetch-error {
  margin-left: 12px;
  font-size: 12px;
  color: #f56c6c;
}
</style>
