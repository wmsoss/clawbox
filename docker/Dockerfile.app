# docker/Dockerfile.app — 大龙虾应用层镜像
# 基于 dalongxia-base 构建，安装应用级依赖 + 代码
# 按白皮书 §10 分层：base(OS+ 系统级) → app(Python deps+ 代码)

FROM dalongxia-base:latest

WORKDIR /app

# ── 1. 后端 Python 依赖
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── 2. 安装 OpenClaw (npm 全局包)
RUN npm cache clean --force && npm install -g openclaw@latest clawhub --prefer-offline=false

# ── 3. 前端代码（映射 volume，启动时构建）
# 前端代码通过 docker-compose.yml 映射到 /app/frontend
# 构建在 start.sh 中完成，产物输出到 /app/static

# ── 4. 应用代码
COPY backend/ /app/backend/

# ── 5. supervisord 配置
COPY docker/supervisord.conf /etc/supervisor/conf.d/dalongxia.conf

# ── 6. 种子配置文件
COPY seeds/openclaw.json /app/seeds/openclaw.json

# ── 7. 启动脚本
COPY scripts/start.sh /start.sh
RUN chmod +x /start.sh

# ── 8. 创建运行时目录
RUN mkdir -p /app/config /app/db /app/workspace/chrome_profile /app/skills \
    /app/openclaw-home/workspace /app/openclaw-home/state /var/log/supervisor

CMD ["/start.sh"]
