<template>
  <div class="step-container">
    <h3>大模型 (LLM) 接入</h3>
    <p class="desc">请选择大龙虾引擎驱动所需的模型提供商。</p>

    <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
      <el-form-item label="提供商" prop="provider">
        <el-select v-model="form.provider" @change="handleProviderChange" placeholder="选择服务商">
          <el-option label="阿里云百炼" value="bailian" />
          <el-option label="DeepSeek 官方" value="deepseek" />
          <el-option label="OpenAI API" value="openai" />
          <el-option label="Anthropic" value="anthropic" />
          <el-option label="Google Gemini" value="gemini" />
          <el-option label="自定义 (Custom)" value="custom" />
        </el-select>
      </el-form-item>

      <!-- Base URL: bailian 和 custom 可编辑, 其他大厂隐藏 -->
      <el-form-item 
        v-if="form.provider === 'bailian'" 
        label="Base URL"
        prop="custom_base_url"
      >
        <el-input 
          v-model="form.custom_base_url" 
          placeholder="标准版: https://dashscope.aliyuncs.com/compatible-mode/v1 | Coding Plan: https://coding.dashscope.aliyuncs.com/v1" 
        />
        <div class="base-url-hint">
          标准版: dashscope.aliyuncs.com/compatible-mode/v1<br />
          Coding Plan: coding.dashscope.aliyuncs.com/v1
        </div>
      </el-form-item>

      <el-form-item 
        v-if="form.provider === 'custom'" 
        label="Base URL" 
        prop="custom_base_url"
      >
        <el-input v-model="form.custom_base_url" placeholder="https://api.example.com/v1" />
      </el-form-item>

      <el-form-item label="API Key" prop="api_key">
        <el-input
          v-model="form.api_key"
          type="password"
          show-password
          placeholder="sk-..."
        />
        <div style="display: flex; align-items: center; width: 100%; margin-top: 8px;">
          <!-- custom 和 bailian 不显示按钮，其他提供商显示按钮但没有 API Key 时置灰 -->
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
          <el-option 
            v-for="m in availableModels" 
            :key="m" 
            :label="m" 
            :value="m" 
          />
        </el-select>
      </el-form-item>
    </el-form>

    <div class="actions">
      <el-button @click="goBack">上一步</el-button>
      <el-button type="primary" @click="submitLLM">下一步</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSetupStore } from '@/stores/setup'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { apiFetch } from '@/utils/api'

const emit = defineEmits(['next'])
const router = useRouter()
const setup = useSetupStore()
const formRef = ref<FormInstance>()
const loadingModels = ref(false)
const fetchError = ref(false)

// 白皮书 §7.1: 仅 bailian (阿里云百炼 Coding Plan) 使用预设模型列表，其他提供商通过 API 动态获取
const PRESET_MODELS: Record<string, string[]> = {
  // Bailian (阿里云百炼 Coding Plan) 模型列表写死
  bailian: ['qwen3.5-plus', 'qwen3-max-2026-01-23', 'qwen3-coder-next', 'qwen3-coder-plus', 'glm-5', 'glm-4.7', 'kimi-k2.5', 'MiniMax-M2.5'],
}

const PRESET_BASE_URLS: Record<string, string> = {
  bailian: '',  // 百炼不预填，由用户选择标准版或 Coding Plan
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
      if ((form.provider === 'custom' || form.provider === 'bailian') && !value) {
        callback(new Error('请输入 Base URL'))
      } else {
        callback()
      }
    }, trigger: 'blur' 
  }]
})

onMounted(() => {
  if (setup.configData.llm) {
    Object.assign(form, setup.configData.llm)
    // 恢复上次选择的模型列表：只有 bailian 使用预设列表，其他需要重新获取
    if (form.provider === 'bailian') {
      availableModels.value = [...(PRESET_MODELS.bailian || [])]
      if (!form.model_name && availableModels.value.length > 0) {
        form.model_name = availableModels.value[0]!
      }
    }
  } else {
    handleProviderChange('bailian')
  }
})

function handleProviderChange(val: string) {
  form.model_name = ''
  fetchError.value = false
  availableModels.value = []

  // 设置 Base URL: bailian 只读展示固定值，custom 可编辑，其他隐藏
  if (val === 'bailian') {
    form.custom_base_url = PRESET_BASE_URLS.bailian!
  } else if (val === 'custom') {
    form.custom_base_url = ''
  } else {
    // 其他提供商（deepseek/openai/anthropic/gemini）不展示 Base URL 字段
    form.custom_base_url = PRESET_BASE_URLS[val] || ''
  }

  // 只有 bailian 使用预设模型列表，其他提供商需要点击"获取模型列表"按钮动态拉取
  if (val === 'bailian') {
    availableModels.value = [...(PRESET_MODELS.bailian || [])]
    if (availableModels.value.length > 0) {
      form.model_name = availableModels.value[0]!
    }
  }
  // 其他提供商：模型列表为空，用户需点击按钮获取
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

    // 调用后端 GET /api/v1/llm/models 动态拉取
    const res = await apiFetch(`/api/v1/llm/models?${params.toString()}`)
    const models = res.models || []

    if (models.length > 0) {
      availableModels.value = models
      // 保留已选模型（如果还在列表中），否则选第一个
      if (!models.includes(form.model_name)) {
        form.model_name = models[0]
      }
      ElMessage.success(`成功拉取 ${models.length} 个可用模型`)
    } else {
      throw new Error('未获取到模型列表')
    }
  } catch (err) {
    fetchError.value = true
  } finally {
    loadingModels.value = false
  }
}

function goBack() {
  router.push({ query: { step: 1 } })
}

async function submitLLM() {
  if (!formRef.value) return
  await formRef.value.validate((valid) => {
    if (valid) {
      setup.configData.llm = { ...form }
      emit('next')
    }
  })
}
</script>

<style scoped>
.step-container {
  max-width: 600px;
  margin: 0 auto;
}
.desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 2rem;
}
.fetch-error {
  margin-left: 12px;
  font-size: 12px;
  color: #f56c6c;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 2rem;
  gap: 12px;
}
.base-url-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin-top: 4px;
}
</style>
