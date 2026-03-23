<template>
  <div class="wizard-container">
    <el-card class="wizard-card">
      <template #header>
        <div class="card-header">
          <h2>大龙虾引擎 - 深度安装向导</h2>
        </div>
      </template>
      
      <el-steps :active="currentStep" finish-status="success" align-center class="mb-4">
        <el-step title="管理员设置" />
        <el-step title="网络环境" />
        <el-step title="大模型接入" />
        <el-step title="就绪" />
      </el-steps>

      <div class="step-content">
        <component 
          :is="stepComponents[currentStep]" 
          @next="nextStep"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Step0Admin from '@/components/wizard/Step0Admin.vue'
import Step1Network from '@/components/wizard/Step1Network.vue'
import Step2LLM from '@/components/wizard/Step2LLM.vue'
import Step3Finish from '@/components/wizard/Step3Finish.vue'

const route = useRoute()
const router = useRouter()

const stepComponents = [
  markRaw(Step0Admin),
  markRaw(Step1Network),
  markRaw(Step2LLM),
  markRaw(Step3Finish)
]

const currentStep = computed(() => {
  const step = Number(route.query.step) || 0
  return Math.max(0, Math.min(step, 3))
})

function nextStep() {
  const next = currentStep.value + 1
  if (next < 4) {
    router.push({ query: { step: next } })
  }
}
</script>

<style scoped>
.wizard-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 2rem;
}
.wizard-card {
  width: 100%;
  max-width: 800px;
}
.card-header h2 {
  margin: 0;
  text-align: center;
}
.mb-4 {
  margin-bottom: 2rem;
}
.step-content {
  min-height: 300px;
}
</style>
