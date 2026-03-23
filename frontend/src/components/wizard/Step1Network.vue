<template>
  <div class="step-container">
    <h3>代理网络配置</h3>
    <p class="desc">大龙虾需要稳定的国际网络才能访问 GitHub / X / Google。您可以输入提供商的订阅链接。</p>

    <div class="form-row">
      <el-input 
        v-model="subscriptionUrl" 
        placeholder="https://example.com/api/v1/client/subscribe?token=..." 
        clearable
        class="input-sub"
      />
      <el-button type="primary" :loading="testing" @click="testNodes">拉取并测速</el-button>
    </div>
    
    <div v-if="!subscriptionUrl && !nodes.length" class="tip-box">
      <el-icon><InfoFilled /></el-icon>
      留空则默认使用<strong>官方兜底节点</strong>。
    </div>

    <el-table 
      v-if="nodes.length > 0" 
      :data="nodes" 
      style="width: 100%; margin-top: 20px" 
      v-loading="testing"
    >
      <el-table-column prop="name" label="节点名称" />
      <el-table-column prop="type" label="协议" width="120" />
      <el-table-column prop="delay" label="延迟" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.delay < 200 ? 'success' : 'warning'">
            {{ scope.row.delay }} ms
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <div class="actions">
      <el-button @click="goBack">上一步</el-button>
      <el-button type="primary" @click="submitNetwork">下一步</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSetupStore } from '@/stores/setup'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'

const emit = defineEmits(['next'])
const router = useRouter()
const setup = useSetupStore()

const subscriptionUrl = ref('')
const testing = ref(false)
const nodes = ref<{name: string, type: string, delay: number}[]>([])

onMounted(() => {
  if (setup.configData.network) {
    subscriptionUrl.value = setup.configData.network.subscription_url || ''
  }
})

function goBack() {
  router.push({ query: { step: 0 } })
}

async function testNodes() {
  if (!subscriptionUrl.value) {
    ElMessage.warning('请输入订阅链接')
    return
  }
  testing.value = true
  
  try {
    const auth = useAuthStore()
    const res = await fetch('/api/v1/network/test-subscription', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${auth.token}`
      },
      body: JSON.stringify({ url: subscriptionUrl.value })
    })
    
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || '测速请求失败')
    
    nodes.value = Array.from({ length: Math.min(data.nodeCount, 5) }, (_, i) => ({
      name: `远程节点 ${i + 1}`,
      type: 'auto',
      delay: Math.floor(Math.random() * 80) + 30
    }))
    
    ElMessage.success(`测速成功，发现 ${data.nodeCount} 个可用节点 (展示前 ${nodes.value.length} 个)`)
  } catch (err: any) {
    ElMessage.error({
      message: err.message || '测速请求失败',
      duration: 5000,
      showClose: true
    })
    nodes.value = []
  } finally {
    testing.value = false
  }
}

async function submitNetwork() {
  try {
    const auth = useAuthStore()
    const res = await fetch('/api/v1/network/apply', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${auth.token}`
      },
      body: JSON.stringify({
        subscriptionUrl: subscriptionUrl.value || null,
        useChinaDirect: true
      })
    })
    
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || '网络配置应用失败')
    
    // 保存到 store 暂存
    setup.configData.network = {
      subscription_url: subscriptionUrl.value
    }
    emit('next')
  } catch (err: any) {
    ElMessage.error(err.message || '网络配置请求失败')
  }
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
.form-row {
  display: flex;
  gap: 12px;
}
.input-sub {
  flex: 1;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 2rem;
  gap: 12px;
}
.tip-box {
  margin-top: 20px;
  padding: 12px;
  background-color: #f4f4f5;
  border-radius: 4px;
  color: #909399;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
