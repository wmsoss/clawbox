# backend/routers/agent.py — OpenClaw Gateway 控制 + 配置 CRUD
# 按白皮书 V3.6 §11.7 实现

import asyncio
import json
import os
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, Body

from backend.services.config_builder import load_current_config, deep_merge, save_config
from backend.services.singbox_manager import _supervisorctl

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])

OPENCLAW_ENV = {
    "OPENCLAW_HOME": "/app/openclaw-home",
    "OPENCLAW_CONFIG_PATH": "/app/config/openclaw.json",
}


async def _openclaw_cmd(*args, timeout=15) -> dict:
    """执行 openclaw CLI 命令，返回解析后的 JSON 输出"""
    proc = await asyncio.create_subprocess_exec(
        "openclaw", *args, "--json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **OPENCLAW_ENV},
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip())
    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError:
        return {"raw": stdout.decode().strip()}


# ── Gateway 进程控制 ────────────────────────────────────────

@router.post("/start")
async def start_agent():
    """启动 OpenClaw Gateway (通过 supervisorctl)"""
    try:
        await _supervisorctl("start", "openclaw")
        return {"status": "starting"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"supervisorctl start failed: {str(e)}")


@router.post("/stop")
async def stop_agent():
    """停止 OpenClaw Gateway"""
    try:
        await _supervisorctl("stop", "openclaw")
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"supervisorctl stop failed: {str(e)}")


@router.post("/restart")
async def restart_agent():
    """重启 OpenClaw Gateway"""
    try:
        try:
            await _supervisorctl("stop", "openclaw")
        except RuntimeError:
            pass
        await _supervisorctl("start", "openclaw")
        return {"status": "restarting"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"supervisorctl restart failed: {str(e)}")


@router.get("/status")
async def agent_status():
    """获取 Gateway 运行状态"""
    try:
        result = await _supervisorctl("status", "openclaw", capture=True)
        parts = result.split()
        state = parts[1] if len(parts) >= 2 else "UNKNOWN"
        return {"status": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"supervisorctl status failed: {str(e)}")


@router.get("/health")
async def agent_health():
    """调用 openclaw health --json 获取 Gateway 健康详情"""
    try:
        return await _openclaw_cmd("health")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"health check failed: {str(e)}")


@router.get("/models")
async def agent_models():
    """调用 openclaw models status --json 获取当前模型状态"""
    try:
        return await _openclaw_cmd("models", "status")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"models status failed: {str(e)}")


@router.post("/models/set")
async def set_model(model: str):
    """切换主模型，无需重启 Gateway"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "openclaw", "models", "set", model,
            env={**os.environ, **OPENCLAW_ENV},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())
        return {"status": "ok", "model": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"model set failed: {str(e)}")


@router.get("/ui-url")
async def agent_ui_url():
    """返回 Gateway Web Control UI 地址"""
    return {"url": "http://localhost:18789/"}


# ── 配置 CRUD ──────────────────────────────────────────────

@router.get("/config")
async def get_agent_config():
    """获取当前 openclaw.json 配置内容"""
    config = await load_current_config()
    return config


@router.put("/config")
async def update_agent_config(payload: dict = Body(...)):
    """
    Deep Merge 更新配置。
    前端提交的 JSON 作为 patch 与现有配置深度合并，不会全量覆写。
    保存后自动重启 OpenClaw Gateway 使配置生效。
    """
    current = await load_current_config()
    merged = deep_merge(current, payload)
    await save_config(merged)

    # 重启 OpenClaw Gateway 使配置生效
    try:
        await _supervisorctl("restart", "openclaw")
    except Exception as e:
        log.warning(f"Failed to restart openclaw after config update: {e}")

    return {"status": "ok", "message": "配置已更新并重启 Gateway"}


# ── 资源监控 ──────────────────────────────────────────────

@router.get("/resources", tags=["Health"])
async def get_resource_usage():
    """前端 Dashboard 轮询，展示内存/CPU 使用率"""
    try:
        import psutil
        return {
            "memory_percent": round(psutil.virtual_memory().percent, 1),
            "cpu_percent": round(psutil.cpu_percent(interval=0.1), 1),
            "memory_available_mb": psutil.virtual_memory().available // 1024 // 1024,
        }
    except ImportError:
        return {
            "memory_percent": 0,
            "cpu_percent": 0,
            "memory_available_mb": 0,
        }
