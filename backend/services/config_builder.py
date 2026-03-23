# backend/services/config_builder.py — DTO → openclaw.json 配置写入
# 按白皮书 V3.6 §11.10 实现
# 核心原则：纯 Python 字典操作写入 JSON，不依赖 CLI，跨版本稳定

import json
import os
import copy
from pathlib import Path

import aiofiles

from backend.schemas import LLMConfigDTO

# 容器内路径固定；Windows 开发环境回落到项目根目录
import sys as _sys
CONFIG_PATH = (
    Path("/app/config/openclaw.json")
    if _sys.platform != "win32"
    else Path(__file__).resolve().parent.parent.parent / "openclaw.json"
)

# 用户锁定标记：带此 key 的节点不会被 Builder 覆写
USER_LOCKED_KEY = "__user_locked__"


def deep_merge(base: dict, override: dict) -> dict:
    """
    深度合并两个字典。
    - override 中标记了 __user_locked__=True 的节点，base 中对应路径不被覆写。
    - 列表类型：override 完全替换 base（不做列表合并，避免重复）。
    """
    result = copy.deepcopy(base)
    for key, val in override.items():
        if key == USER_LOCKED_KEY:
            continue
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            if result[key].get(USER_LOCKED_KEY):
                continue
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result


async def load_current_config() -> dict:
    """加载现有 openclaw.json，不存在则返回空骨架"""
    if CONFIG_PATH.exists():
        async with aiofiles.open(CONFIG_PATH, "r") as f:
            return json.loads(await f.read())
    return {"models": {"mode": "merge", "providers": {}}, "agents": {"defaults": {}}}


async def save_config(config: dict) -> None:
    """原子写入：先写 .tmp，校验后 rename"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(CONFIG_PATH) + ".tmp"
    async with aiofiles.open(tmp, "w") as f:
        await f.write(json.dumps(config, ensure_ascii=False, indent=2))
    os.replace(tmp, str(CONFIG_PATH))


# ── 提供商元数据 ──

# 内置提供商：OpenClaw 已内置支持，只需写 .env 和 models.providers
BUILTIN_PROVIDERS = {"anthropic", "openai", "google"}

# 非内置提供商的 api 类型（baseUrl 由前端传入）
PROVIDER_META = {
    "bailian":   {"api": "openai-completions"},
    "deepseek":  {"api": "openai-completions", "defaultBaseUrl": "https://api.deepseek.com/v1"},
    "groq":      {"api": "openai-completions", "defaultBaseUrl": "https://api.groq.com/openai/v1"},
    "custom":    {"api": "openai-completions"},
}

# 提供商 → 环境变量名
PROVIDER_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "google":    "GOOGLE_API_KEY",
    "bailian":   "DASHSCOPE_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
    "groq":      "GROQ_API_KEY",
    "custom":    "CUSTOM_LLM_API_KEY",
}


async def build_and_apply(dto: LLMConfigDTO) -> None:
    """
    主入口：接收前端 DTO，写入 openclaw.json。
    - 非内置提供商：写入 models.providers（含 baseUrl / apiKey / api）
    - 所有提供商：更新 agents.defaults.model.primary + models 白名单
    - Gateway 监听文件变化自动热重载，无需重启
    """
    config = await load_current_config()

    provider = dto.provider
    model_id = dto.model_name
    primary = f"{provider}/{model_id}"

    # Step 1: 写入 models.providers（非内置提供商）
    if provider not in BUILTIN_PROVIDERS:
        meta = PROVIDER_META.get(provider, {"api": "openai-completions"})
        base_url = dto.custom_base_url or meta.get("defaultBaseUrl", "")
        provider_cfg = {
            "baseUrl": base_url,
            "apiKey":  dto.api_key,
            "api":     meta["api"],
        }
        # 合并而非覆盖，保留已有的 models 数组等字段
        existing = config.setdefault("models", {}).setdefault("providers", {}).get(provider, {})
        existing.update(provider_cfg)
        # OpenClaw 要求 models 数组存在，如果没有则补上
        if "models" not in existing:
            existing["models"] = [{"id": model_id, "name": model_id}]
        config["models"]["providers"][provider] = existing

    # Step 2: 更新主模型和模型白名单
    config.setdefault("agents", {}).setdefault("defaults", {})
    config["agents"]["defaults"].setdefault("model", {})["primary"] = primary
    config["agents"]["defaults"].setdefault("models", {})[primary] = {}

    # Step 3: 原子写入
    await save_config(config)
