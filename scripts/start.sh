#!/bin/bash
# scripts/start.sh — ClawBox 容器启动脚本
# 职责：初始化运行时目录 + 种子配置 + 前端构建 → 启动 supervisord

set -e

echo "=== ClawBox 容器启动 ==="

# ── OpenClaw 初始化 ──
export OPENCLAW_HOME=/app/openclaw-home
export OPENCLAW_CONFIG_PATH=/app/config/openclaw.json

# 创建必要目录
mkdir -p "$OPENCLAW_HOME/workspace" "$OPENCLAW_HOME/state"
mkdir -p /app/config
mkdir -p /app/static/assets

# 写入种子配置（仅首次，不覆盖已有配置）
# 如果配置文件不存在或格式错误，从种子配置复制
if [ ! -f "$OPENCLAW_CONFIG_PATH" ]; then
    cp /app/seeds/openclaw.json "$OPENCLAW_CONFIG_PATH"
    echo "=== ClawBox：已写入 OpenClaw 种子配置 ==="
else
    # 检查配置文件 JSON 格式是否有效（不用 openclaw doctor，它在初始化阶段不可靠）
    if ! python3 -c "import json; json.load(open('$OPENCLAW_CONFIG_PATH'))" 2>/dev/null; then
        echo "警告：openclaw.json 格式无效，备份并重置配置..."
        cp "$OPENCLAW_CONFIG_PATH" "${OPENCLAW_CONFIG_PATH}.bak.$(date +%Y%m%d%H%M%S)"
        cp /app/seeds/openclaw.json "$OPENCLAW_CONFIG_PATH"
        echo "已重置为最新种子配置，原配置已备份"
    fi
fi

# ── Sing-box 初始化 ──
# 无配置文件时写入最小直连配置，防止 supervisord 启动失败
if [ ! -f /app/config/singbox.json ]; then
    echo "singbox.json 不存在，写入最小直连配置..."
    cat > /app/config/singbox.json <<'EOF'
{
  "log": { "level": "warn" },
  "dns": {
    "servers": [
      { "type": "udp", "tag": "dns-local", "server": "223.5.5.5" }
    ]
  },
  "inbounds": [
    { "type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 2080 }
  ],
  "outbounds": [
    { "type": "direct", "tag": "direct" }
  ],
  "route": {
    "default_domain_resolver": { "server": "dns-local" },
    "final": "direct",
    "auto_detect_interface": true
  }
}
EOF
fi

# ── 前端构建 ──
# 如果前端静态文件不存在，则构建前端
# 注意：vite.config.ts 已配置 outDir 为 /app/static，npm run build 直接输出到目标目录
if [ ! -f /app/static/index.html ]; then
    echo "前端静态文件不存在，开始构建..."
    cd /app/frontend
    export VITE_OUT_DIR=/app/static
    npm ci --silent 2>/dev/null || npm install --silent
    npm run build --silent
    echo "=== ClawBox：前端构建完成 ==="
fi

# ── OpenClaw Skills 预装（仅首次，后台运行不阻塞） ──
# 在后台运行，不阻塞 supervisord 启动
if [ ! -d /app/skills/agent-commons ]; then
    echo "预装 OpenClaw Skills (后台运行)..."
    (
      git clone --depth=1 https://github.com/openclaw/skills.git /tmp/openclaw-skills 2>/dev/null || true
      if [ -d /tmp/openclaw-skills/skills ]; then
          cp -r /tmp/openclaw-skills/skills/* /app/skills/ 2>/dev/null || true
          rm -rf /tmp/openclaw-skills
          echo "=== OpenClaw Skills 预装完成 ==="
      fi
    ) &
fi

# ── 启动 supervisord ──
echo "启动 supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/clawbox.conf
