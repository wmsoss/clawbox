<template>
  <div class="xterm-container" ref="terminalRef"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, shallowRef } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from '@xterm/addon-fit'
import 'xterm/css/xterm.css'
import { useAuthStore } from '@/stores/auth'

const terminalRef = ref<HTMLDivElement>()
const term = shallowRef<Terminal | null>(null)
const fitAddon = shallowRef<FitAddon | null>(null)
const socket = shallowRef<WebSocket | null>(null)
const auth = useAuthStore()

onMounted(() => {
  if (!terminalRef.value) return

  // 1. Init xterm.js
  const t = new Terminal({
    cursorBlink: true,
    fontFamily: '"Cascadia Code", "Fira Code", monospace',
    fontSize: 14,
    theme: {
      background: '#1e1e1e'
    }
  })
  
  const fit = new FitAddon()
  t.loadAddon(fit)
  
  t.open(terminalRef.value)
  fit.fit()
  
  term.value = t
  fitAddon.value = fit

  // 2. Connect to backend PTY WebSocket
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${window.location.host}/ws/pty?token=${auth.token || ''}`
  const ws = new WebSocket(wsUrl)
  
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    // 启动后立即发送当前终端尺寸
    sendResize(ws, fit)
    window.addEventListener('resize', handleResize)
  }

  ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      const decoder = new TextDecoder()
      t.write(decoder.decode(event.data))
    } else if (typeof event.data === 'string') {
      t.write(event.data)
    }
  }

  ws.onclose = () => {
    t.writeln('\n\x1b[31m[PTY 连接已断开]\x1b[0m')
  }

  ws.onerror = () => {
    t.writeln('\n\x1b[31m[WebSocket 连接失败]\x1b[0m')
  }

  socket.value = ws

  // 3. User Input -> WS
  t.onData((data) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  })
})

/**
 * 发送终端尺寸调整命令 (JSON 协议)
 */
function sendResize(ws: WebSocket, fit: FitAddon) {
  if (ws.readyState !== WebSocket.OPEN) return
  fit.fit()
  const dims = fit.proposeDimensions()
  if (dims) {
    ws.send(JSON.stringify({
      type: 'resize',
      cols: dims.cols,
      rows: dims.rows,
    }))
  }
}

const handleResize = () => {
  const fit = fitAddon.value
  const ws = socket.value
  if (fit && ws) {
    sendResize(ws, fit)
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (socket.value) {
    socket.value.close()
  }
  if (term.value) {
    term.value.dispose()
  }
})
</script>

<style scoped>
.xterm-container {
  width: 100%;
  height: 100%;
  min-height: 250px;
  padding: 8px;
  box-sizing: border-box;
  background-color: #1e1e1e;
  border-radius: 4px;
}
</style>
