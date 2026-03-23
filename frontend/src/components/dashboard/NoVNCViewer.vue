<template>
  <div class="novnc-container">
    <iframe
      class="novnc-iframe"
      :src="vncUrl"
      style="border: 0;"
      allowfullscreen
    ></iframe>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// VNC Viewer wrapper based on iframe.
// In dev mode, Vite proxy handles /vnc. In container, noVNC is on port 6080.
// Default to port 6080 on current hostname for container deployment.
const vncUrl = computed(() => {
  const host = window.location.hostname
  return `http://${host}:6080/vnc.html?autoconnect=true&resize=remote`
})
</script>

<style scoped>
.novnc-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background-color: #2b2b2b;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.novnc-iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
</style>
