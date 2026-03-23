# 贡献指南 | Contributing Guide

感谢你对 ClawBox 的关注！欢迎任何形式的贡献。

## 如何贡献

### 报告 Bug
1. 在 [Issues](https://github.com/wmsoss/clawbox/issues) 页面创建新 Issue
2. 使用 Bug 报告模板，包含：
   - 操作系统和 Docker 版本
   - 复现步骤
   - 期望行为 vs 实际行为
   - 错误日志截图

### 提交功能建议
1. 在 Issues 页面创建 Feature Request
2. 描述你想要的功能，以及使用场景

### 提交代码 (Pull Request)
1. **Fork** 本仓库
2. 创建功能分支：`git checkout -b feature/my-feature`
3. 提交修改：`git commit -m "feat: 添加某功能"`
4. 推送分支：`git push origin feature/my-feature`
5. 在 GitHub 上创建 **Pull Request**

### Commit 规范
使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：
```
feat: 新增功能
fix: 修复 Bug
docs: 文档更新
refactor: 代码重构（不影响功能）
style: 代码格式调整
test: 测试相关
chore: 构建/工具链
```

## 开发环境搭建

```bash
# 1. 克隆仓库
git clone https://github.com/wmsoss/clawbox.git
cd clawbox

# 2. 复制环境变量
cp .env.example .env
# 编辑 .env 填入你的 Token

# 3. 构建并启动
docker compose up -d

# 4. 访问
# 主控台：http://localhost:8000
# OpenClaw：http://localhost:18789
```

## 前端开发

```bash
cd frontend
npm install
npm run dev    # 开发模式 (HMR)
npm run build  # 构建到 app/static/
```

## 后端开发

后端代码通过 Docker volume 映射，修改后自动生效（uvicorn --reload）。

## 代码规范
- 后端：Python 3.11+，遵循 PEP 8
- 前端：Vue 3 + TypeScript，ESLint
- 注释和 commit message 使用中文

## 行为准则
请保持友善和尊重。恶意攻击、歧视性言论、垃圾信息将被移除。

## 许可证
本项目使用 [BSL-1.1](LICENSE) 许可证。提交 PR 即表示你同意你的贡献适用相同许可证。

---
*Thank you for contributing to ClawBox! 🦞*
