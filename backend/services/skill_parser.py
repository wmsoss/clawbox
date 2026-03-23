# backend/services/skill_parser.py — Awesome-Skills README 解析 + 技能安装逻辑
# 按白皮书 §9.1-§9.2 实现
# Task 2.6: SkillParser.parse_readme() + install_skill() + uninstall_skill()
# 注意：_supervisorctl 从 singbox_manager 导入，不创建 supervisor_client.py (Guardrail #11)

import asyncio
import re
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import InstalledSkill
from backend.services.singbox_manager import _supervisorctl

SKILLS_DIR = Path("/app/skills")

# ── README 解析 ──────────────────────────────────────────


@dataclass
class SkillCard:
    """从 README.md 解析出的技能卡片"""
    category: str          # H2/H3 标题作为分类名
    name: str              # 技能名称
    repo_url: str          # GitHub 仓库地址
    description: str = ""  # 技能描述

    def to_dict(self) -> dict:
        return asdict(self)


class SkillParser:
    """
    解析 awesome-openclaw-skills README.md 格式：

    ## 分类名
    - [技能名](https://github.com/xxx/yyy) — 描述文本
    - [技能名2](https://github.com/xxx/zzz) — 描述文本2

    ### 子分类名
    - [技能名3](https://github.com/xxx/aaa) — 描述文本3
    """

    # 匹配列表项：- [name](url) — description 或 - [name](url) - description
    _SKILL_PATTERN = re.compile(
        r"^[-*]\s+\[([^\]]+)\]\(([^)]+)\)\s*(?:[—\-–]\s*(.*))?$"
    )

    # 匹配 HTML 格式的 H3 标题：<h3 style="display:inline">分类名</h3>
    _HTML_H3_PATTERN = re.compile(
        r"<h3[^>]*>\s*(.*?)\s*</h3>",
        re.IGNORECASE
    )

    def parse_readme(self, raw_md: str) -> List[SkillCard]:
        """
        解析 README.md 原始文本，提取 H2/H3 为分类（支持 Markdown 和 HTML 格式），列表项为技能卡片。

        Returns:
            技能卡片列表，每个包含 category/name/repo_url/description
        """
        cards: List[SkillCard] = []
        current_category = ""

        for line in raw_md.splitlines():
            stripped = line.strip()

            # H2 标题 → 主分类 (Markdown 格式)
            if stripped.startswith("## "):
                current_category = stripped.lstrip("# ").strip()
                continue

            # H3 标题 → 子分类 (Markdown 格式)
            if stripped.startswith("### "):
                current_category = stripped.lstrip("# ").strip()
                continue

            # H3 标题 → 分类 (HTML 格式，用于<details><summary>结构)
            html_match = self._HTML_H3_PATTERN.search(stripped)
            if html_match:
                current_category = html_match.group(1).strip()
                continue

            # 列表项 → 技能卡片
            match = self._SKILL_PATTERN.match(stripped)
            if match and current_category:
                name = match.group(1).strip()
                repo_url = match.group(2).strip()
                description = (match.group(3) or "").strip()
                cards.append(SkillCard(
                    category=current_category,
                    name=name,
                    repo_url=repo_url,
                    description=description,
                ))

        return cards


# ── 技能安装（安全流程：backup → validate → atomic replace → DB → restart） ──


async def install_skill(repo_url: str, name: str, db: AsyncSession) -> None:
    """
    技能安装的完整安全流程（白皮书 §9.2）：
    1. clone 到临时目录
    2. 校验目录结构合规性 (必须含 skill.yaml 或 index.js)
    3. 原子替换到正式目录（先备份旧版本）
    4. 更新数据库
    5. 触发 OpenClaw 重启（§11.3 约定使用 supervisorctl restart）
    失败时任何步骤均回滚，不影响已运行的技能
    """
    tmp_dir = Path(f"/tmp/skill_install_{name}")
    final_dir = SKILLS_DIR / name
    backup_dir = Path(f"/tmp/skill_backup_{name}")

    try:
        # ── Step 0: 清理可能残留的临时目录
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)

        # ── Step 1: clone 到临时目录
        clone_env = {
            "GIT_TERMINAL_PROMPT": "0",
            # 使用 Sing-box SOCKS5 代理，避免 GFW 干扰
            "GIT_CONFIG_PARAMETERS": "'http.proxy=socks5://127.0.0.1:2080'",
        }
        if settings.github_token:
            clone_env["GITHUB_TOKEN"] = settings.github_token

        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", repo_url, str(tmp_dir),
            env=clone_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(f"git clone 失败: {stderr.decode().strip()}")

        # ── Step 2: 校验目录结构
        has_manifest = (tmp_dir / "skill.yaml").exists() or (tmp_dir / "index.js").exists()
        if not has_manifest:
            raise ValueError("技能包缺少 skill.yaml 或 index.js，目录结构不合规")

        # ── Step 3: 原子替换（先备份旧版本）
        if final_dir.exists():
            shutil.copytree(final_dir, backup_dir)
            shutil.rmtree(final_dir)
        shutil.move(str(tmp_dir), str(final_dir))

        # ── Step 4: 更新数据库（upsert 语义：存在则更新，不存在则插入）
        result = await db.execute(
            select(InstalledSkill).where(InstalledSkill.name == name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.repo_url = repo_url
            existing.install_path = str(final_dir)
            existing.last_error = None
        else:
            skill = InstalledSkill(
                name=name,
                repo_url=repo_url,
                install_path=str(final_dir),
            )
            db.add(skill)
        await db.flush()

        # ── Step 5: 热重载 OpenClaw（§11.3: supervisorctl restart）
        await _supervisorctl("restart", "openclaw")

    except Exception as e:
        # 回滚：恢复备份（如果有）
        if backup_dir.exists() and not final_dir.exists():
            shutil.move(str(backup_dir), str(final_dir))

        # 记录错误到数据库（仅针对已存在的记录）
        try:
            result = await db.execute(
                select(InstalledSkill).where(InstalledSkill.name == name)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.last_error = str(e)
                await db.flush()
        except Exception:
            pass  # 数据库记录失败不应掩盖原始错误

        raise

    finally:
        # 清理临时文件
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)


# ── 技能卸载 ──────────────────────────────────────────


async def uninstall_skill(name: str, db: AsyncSession) -> None:
    """
    卸载技能：移除目录 → 删除数据库记录 → 重启 OpenClaw
    """
    final_dir = SKILLS_DIR / name

    # 删除技能目录
    if final_dir.exists():
        shutil.rmtree(final_dir)

    # 删除数据库记录
    await db.execute(
        delete(InstalledSkill).where(InstalledSkill.name == name)
    )
    await db.flush()

    # 重启 OpenClaw 使变更生效
    await _supervisorctl("restart", "openclaw")
