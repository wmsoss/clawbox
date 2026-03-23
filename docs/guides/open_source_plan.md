# ClawBox 开源计划

## 一、项目信息

| 项目 | 内容 |
|------|------|
| **项目名** | ClawBox |
| **GitHub 组织** | [wmsoss](https://github.com/wmsoss) |
| **公开仓库** | [wmsoss/clawbox](https://github.com/wmsoss/clawbox) |
| **私有仓库** | wmsoss/clawbox-private |
| **许可证** | BSL-1.1 (4 年后→Apache 2.0) |
| **授权方** | Womso |
| **联系邮箱** | business@womso.com |

---

## 二、仓库结构

采用**嵌套仓库**方案：父目录为私有仓库，子目录 `oss/` 为公开仓库。

```
d:\Projects\clawbox\                    ← 私有仓库 (wmsoss/clawbox-private)
├── .agent/ | CLAUDE.md | 白皮书        ← AI 规则 & 内部文档
├── launcher/                           ← Windows 启动器
├── scripts/                            ← 私有构建脚本
│
└── oss/                                ← 公开仓库 (wmsoss/clawbox)
    ├── backend/ | frontend/ | docker/  ← 项目代码
    ├── README.md | LICENSE             ← 开源必备文件
    └── ...
```

**优势**：
- 私有文件完整版本控制，多设备同步
- 公开仓库全新 git 历史，零私有数据泄露
- AI Agent 规则文件在父目录根，工作区兼容

---

## 三、版本管理

### 语义版本 (SemVer)

格式：`MAJOR.MINOR.PATCH`

| 改动类型 | 版本号变化 | 示例 |
|---------|-----------|------|
| 架构大改 | MAJOR +1 | 1.0.0 → **2.0.0** |
| 新功能 | MINOR +1 | 1.4.0 → **1.5.0** |
| Bug 修复 | PATCH +1 | 1.5.0 → **1.5.1** |

### Git Tag 流程

```bash
# 打 tag
git tag -a v1.5.0 -m "v1.5.0: 项目开源 + 重命名为 ClawBox"

# 推送
git push origin v1.5.0

# 在 GitHub Releases 页面创建 Release，附加二进制附件
```

---

## 四、Docker 镜像发布

### 推荐：Docker Hub + 阿里云 ACR 双推

```bash
# Docker Hub
docker tag clawbox-image:latest wmsoss/clawbox:v1.5.0
docker push wmsoss/clawbox:v1.5.0

# 阿里云 ACR（国内加速）
docker tag clawbox-image:latest registry.cn-hangzhou.aliyuncs.com/wmsoss/clawbox:v1.5.0
docker push registry.cn-hangzhou.aliyuncs.com/wmsoss/clawbox:v1.5.0
```

### Tag 策略

每次发版推 4 个 tag：`latest` + `v1.5.0` + `v1.5` + `v1`

---

## 五、发布检查清单

- [x] 许可证选定 (BSL-1.1)
- [x] 仓库名选定 (wmsoss/clawbox)
- [x] GitHub 组织已创建 (wmsoss)
- [x] README.md (中英双语)
- [x] CONTRIBUTING.md
- [x] .env.example (所有敏感项用占位符)
- [x] LICENSE 文件
- [x] CHANGELOG.md
- [x] .gitignore (干净版，无私有文件)
- [ ] 打第一个 Git Tag
- [ ] 推送镜像到 Docker Hub
- [ ] 注册阿里云 ACR
- [ ] GitHub Releases 创建第一个 Release
- [ ] 开启 GitHub Discussions

---

## 六、日常工作流

```bash
# 1. 公开代码修改 → 在 oss/ 下提交
cd oss/
git add . && git commit -m "feat: xxx" && git push origin main

# 2. 私有文件修改 → 在父目录提交
cd ..
git add . && git commit -m "docs: 更新白皮书" && git push origin main

# 3. 发版
cd oss/
git tag -a v1.5.1 -m "v1.5.1: 修复 xxx"
git push origin v1.5.1
```
