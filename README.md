<div align="center">

# 🦞 ClawBox

**一键部署 OpenClaw AI Agent 的 Docker 沙盒面板**

[English](#english) | [中文](#中文)

[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://hub.docker.com/r/wmsoss/clawbox)

</div>

---

## 中文

### 这是什么？

ClawBox 是一个面向 AI 自动化爱好者的 **一键部署面板**，将 [OpenClaw](https://openclaw.ai) Agent 框架封装在 Docker 容器中，提供：

- 🖥️ **Web 主控台** — 可视化管理 Agent 状态、LLM 配置、技能商店
- 🌐 **noVNC 远程桌面** — 在浏览器中观看 AI 操控 Chrome 浏览器
- 📟 **Web 终端** — 在线 xterm.js 终端，直接操作容器
- 🛡️ **网络隔离** — Sing-box 路由管理，保护你的真实 IP
- 🚀 **桌面版启动器** — 提供 Windows/macOS/Linux 跨平台 GUI 客户端，一键配置拉取极速上手
- 🔒 **开源透明** — 代码完全公开，不窃取任何 API Key 或凭证

### 快速开始

#### 前置要求
- Docker Desktop（Windows/macOS）或 Docker Engine（Linux）
- WSL2（仅 Windows 平台需要）
- 4GB+ 可用内存

#### 选项一：使用桌面启动器（推荐）

ClawBox 提供跨平台桌面客户端，带有全自动环境检测、一键镜像拉取、代码下载及启动向导。

1. 前往 [Releases](https://github.com/wmsoss/clawbox/releases) 页面下载对应系统的安装包（Windows 即选 `.exe`，macOS 选 `.dmg`）
2. 打开 ClawBox Launcher，跟随向导完成运行环境配置：
   
   ![环境检测向导](docs/images/launcher/step_env.png)

3. 在可视化向导中配置网络与大模型 API Key 即可极速启动。

   ![主控台一览](docs/images/launcher/dashboard.png)

#### 选项二：命令行一键启动

```bash
# 1. 克隆仓库
git clone https://github.com/wmsoss/clawbox.git
cd clawbox

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 3. 启动
docker compose up -d

# 4. 访问
# 主控台：http://localhost:8000
# OpenClaw 控制台：http://localhost:18789
```

### 架构概览

```
┌────────────────────────────────────────────┐
│              Docker 容器                    │
│                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ FastAPI   │  │ OpenClaw │  │  Chrome  │ │
│  │ :8000     │  │ :18789   │  │  (CDP)   │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Vue 前端  │  │ Sing-box │  │  noVNC   │ │
│  │ (静态)    │  │ (路由)   │  │  :6080   │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│                                            │
│            Supervisord 进程守护             │
└────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus |
| 后端 | FastAPI (异步) + SQLite |
| Agent | OpenClaw |
| 浏览器 | Chrome + noVNC |
| 网络 | Sing-box |
| 容器 | Docker + Supervisord |
| 启动器 | Tauri v2 (Rust + React/TypeScript) |

### 目录结构

```
clawbox/
├── backend/          # FastAPI 后端
├── frontend/         # Vue 3 前端
├── clawbox-launcher/ # 跨平台桌面启动器 (Tauri v2)
├── docker/           # Dockerfile + supervisord 配置
├── seeds/            # 种子配置文件（模板）
├── scripts/          # 启动脚本
├── .github/workflows # CI/CD（启动器构建 + Docker 镜像构建）
├── docs/             # 文档
├── docker-compose.yml
├── .env.example      # 环境变量模板
├── LICENSE           # BSL-1.1
└── README.md
```

### 常见问题

**Q: 我的 API Key 安全吗？**
A: 是的。所有 Key 仅存储在本地 `.env` 文件中，不会上传到任何服务器。代码完全开源，欢迎审查。

**Q: 支持哪些 LLM 提供商？**
A: 阿里云百炼、DeepSeek、OpenAI、Anthropic、Google Gemini、以及任何 OpenAI 兼容的自定义接口。

**Q: 需要科学上网吗？**
A: OpenClaw 技能安装需要访问 GitHub。容器内置 Sing-box 路由管理，可在主控台配置。

### 贡献

欢迎 PR！请阅读 [贡献指南](CONTRIBUTING.md)。

### 许可证

[Business Source License 1.1](LICENSE) — 个人免费使用，商业用途需获得授权。4 年后自动转为 Apache 2.0。

商业授权联系：business@womso.com

---

## English

### What is this?

ClawBox is a **one-click deployment panel** for AI automation enthusiasts. It packages the [OpenClaw](https://openclaw.ai) Agent framework in a Docker container, providing:

- 🖥️ **Web Dashboard** — Visual management of Agent status, LLM configs, skill store
- 🌐 **noVNC Remote Desktop** — Watch AI control Chrome in your browser
- 📟 **Web Terminal** — Online xterm.js terminal for direct container access
- 🛡️ **Network Isolation** — Sing-box routing to protect your real IP
- 🚀 **Desktop Launcher** — Cross-platform GUI (Windows/macOS/Linux) with auto-update
- 🔒 **Open Source** — Fully transparent code, no key stealing, no backdoors

### Quick Start

```bash
git clone https://github.com/wmsoss/clawbox.git
cd clawbox
cp .env.example .env  # Edit .env with your API keys
docker compose up -d
# Dashboard: http://localhost:8000
# OpenClaw:  http://localhost:18789
```

### License

[Business Source License 1.1](LICENSE) — Free for personal use. Commercial use requires a license. Converts to Apache 2.0 after 4 years.

For commercial licensing: business@womso.com

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://womso.com">Womso</a></sub>
</div>
