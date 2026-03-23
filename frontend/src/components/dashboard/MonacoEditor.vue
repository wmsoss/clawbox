<template>
  <div class="monaco-panel">
    <div class="monaco-header">
      <div class="header-left">
        <el-icon><EditPen /></el-icon>
        <span>openclaw.json 高阶编辑</span>
      </div>
      <div class="header-right">
        <el-button
          type="primary"
          size="small"
          :loading="saving"
          @click="handleSave"
          :disabled="!isDirty"
        >
          保存 (Deep Merge)
        </el-button>
        <el-button
          size="small"
          @click="handleReload"
          :disabled="saving"
        >
          重新加载
        </el-button>
      </div>
    </div>
    <div class="editor-container" ref="editorContainerRef"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, shallowRef } from 'vue'
import { useAgentStore } from '@/stores/agent'
import { ElMessage } from 'element-plus'
import { EditPen } from '@element-plus/icons-vue'

// Monaco worker setup for Vite — must be BEFORE monaco import
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'

self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') return new jsonWorker()
    return new editorWorker()
  }
}

import * as monaco from 'monaco-editor'

const agentStore = useAgentStore()
const editorContainerRef = ref<HTMLDivElement>()
const editor = shallowRef<monaco.editor.IStandaloneCodeEditor | null>(null)
const saving = ref(false)
const isDirty = ref(false)
const initialContent = ref('')

onMounted(async () => {
  // Ensure config is loaded
  if (!agentStore.configRaw) {
    await agentStore.fetchConfig()
  }

  if (!editorContainerRef.value) return

  const ed = monaco.editor.create(editorContainerRef.value, {
    value: agentStore.configRaw || '{\n  \n}',
    language: 'json',
    theme: 'vs-dark',
    minimap: { enabled: false },
    lineNumbers: 'on',
    fontSize: 13,
    fontFamily: '"Cascadia Code", "Fira Code", monospace',
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    automaticLayout: true,
    tabSize: 2,
    renderWhitespace: 'selection',
    bracketPairColorization: { enabled: true },
    padding: { top: 8, bottom: 8 },
  })

  initialContent.value = agentStore.configRaw || ''

  ed.onDidChangeModelContent(() => {
    isDirty.value = ed.getValue() !== initialContent.value
  })

  editor.value = ed
})

// Watch for external config updates (e.g. after AgentConfig fetches)
watch(() => agentStore.configRaw, (newVal) => {
  if (editor.value && newVal && !isDirty.value) {
    editor.value.setValue(newVal)
    initialContent.value = newVal
  }
})

async function handleSave() {
  if (!editor.value) return
  const content = editor.value.getValue()

  // Validate JSON
  try {
    JSON.parse(content)
  } catch (e) {
    ElMessage.error('JSON 格式错误，请修正后再保存')
    return
  }

  saving.value = true
  try {
    await agentStore.saveConfig(content)
    initialContent.value = content
    isDirty.value = false
    ElMessage.success('配置已保存 (Deep Merge 模式)')
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || e))
  } finally {
    saving.value = false
  }
}

async function handleReload() {
  await agentStore.fetchConfig()
  if (editor.value) {
    editor.value.setValue(agentStore.configRaw)
    initialContent.value = agentStore.configRaw
    isDirty.value = false
  }
  ElMessage.info('配置已重新加载')
}

onBeforeUnmount(() => {
  if (editor.value) {
    editor.value.dispose()
    editor.value = null
  }
})
</script>

<style scoped>
.monaco-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 300px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
}

.monaco-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #cccccc;
  font-size: 13px;
  font-weight: 500;
}

.header-right {
  display: flex;
  gap: 8px;
}

.editor-container {
  flex: 1;
  min-height: 250px;
}
</style>
