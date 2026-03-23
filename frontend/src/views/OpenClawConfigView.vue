<template>
  <div class="openclaw-config-view">
    <NavBar />

    <div class="page-content">
      <div class="page-header">
        <h2>OpenClaw 配置 (openclaw.json)</h2>
        <div class="header-actions">
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>保存 (Deep Merge)
          </el-button>
          <el-button @click="handleReload" :loading="loading">
            <el-icon><Refresh /></el-icon>重新加载
          </el-button>
        </div>
      </div>

      <div class="editor-wrapper" ref="editorContainer"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Refresh } from '@element-plus/icons-vue'
import { apiFetch } from '@/utils/api'
import NavBar from '@/components/common/NavBar.vue'
import * as monaco from 'monaco-editor'

const editorContainer = ref<HTMLElement>()
const loading = ref(false)
const saving = ref(false)

let editor: monaco.editor.IStandaloneCodeEditor | null = null

async function loadConfig(): Promise<string> {
  loading.value = true
  try {
    const data = await apiFetch('/api/v1/agent/config')
    return JSON.stringify(data, null, 2)
  } catch (err: any) {
    ElMessage.error('加载配置失败: ' + err.message)
    return '{}'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!editor) return
  const raw = editor.getValue()
  try {
    JSON.parse(raw) // validate JSON
  } catch {
    ElMessage.error('JSON 格式错误，请检查语法')
    return
  }
  saving.value = true
  try {
    await apiFetch('/api/v1/agent/config', {
      method: 'PUT',
      body: raw
    })
    ElMessage.success('配置已保存 (Deep Merge)')
  } catch (err: any) {
    ElMessage.error('保存失败: ' + err.message)
  } finally {
    saving.value = false
  }
}

async function handleReload() {
  if (!editor) return
  const content = await loadConfig()
  editor.setValue(content)
  ElMessage.success('已重新加载')
}

onMounted(async () => {
  await nextTick()
  if (!editorContainer.value) return

  const content = await loadConfig()

  editor = monaco.editor.create(editorContainer.value, {
    value: content,
    language: 'json',
    theme: 'vs-dark',
    automaticLayout: true,
    minimap: { enabled: true },
    folding: true,
    foldingStrategy: 'indentation',
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    fontSize: 14,
    tabSize: 2,
    formatOnPaste: true,
    renderWhitespace: 'selection',
    find: {
      addExtraSpaceOnTop: true,
      autoFindInSelection: 'never',
      seedSearchStringFromSelection: 'always'
    }
  })

  // Ctrl+S 快捷保存
  editor.addAction({
    id: 'save-config',
    label: 'Save Config',
    keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS],
    run: () => handleSave()
  })
})

onBeforeUnmount(() => {
  editor?.dispose()
  editor = null
})
</script>

<style scoped>
.openclaw-config-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.page-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 24px;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.editor-wrapper {
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #dcdfe6;
}
</style>
