# 版本更新日志 (Changelog)

所有重要版本更新记录。格式遵循 [Keep a Changelog](https://keepachangelog.com/)。

## [v1.5.0] - 2026-03-23

### 新增
- 项目正式开源！仓库地址：`github.com/wmsoss/clawbox`

### 变更
- 项目重命名：Dalongxia / OpenClaw-Box → **ClawBox**
- GitHub 组织：wmsoss
- Docker 镜像名：`clawbox-image`，容器名：`clawbox`
- 数据库文件：`clawbox.sqlite`
- 许可证授权方更新为 Womso

## [v1.4.0] - 2026-03-20

### 新增
- OpenClaw 密码认证模式（替代 token 模式）
- 禁用设备配对（`dangerouslyDisableDeviceAuth`）
- Launcher WSL2 安装增强（UAC 提权、轮询检测）

### 修复
- OpenClaw 配置校验改为 `python3 json.load()`，修复循环重启
- `config_builder` 保留 provider 的 `models` 数组
- `sync_password_to_openclaw` 改为直接读写 JSON 文件
- Launcher 隐藏黑色命令窗口闪烁

### 改进
- Launcher 顺序操作流（解压→加载→启动，每步间隔等待）
- Docker Desktop 自动启动逻辑
- 打包文档更新（镜像 vs 代码包规则）

## [v1.3.0] - 2026-03-17

### 新增
- Launcher GUI 启动器
- 安装向导（4 步）
- LLM 配置页面
- 技能商店
- noVNC 远程桌面集成
- Web 终端（xterm.js）
