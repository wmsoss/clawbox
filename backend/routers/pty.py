# backend/routers/pty.py — PTY WebSocket 端点
# 按白皮书 §5.7 实现：真实双向 PTY，支持 resize，finally 强制清理
# Windows 开发环境使用 asyncio.subprocess 降级方案

import asyncio
import json
import logging
import sys

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from starlette.websockets import WebSocketState

from backend.config import settings

# ptyprocess is Unix-only, handle Windows dev environment gracefully
if sys.platform != "win32":
    import ptyprocess
else:
    ptyprocess = None

router = APIRouter()


async def verify_token(token: str) -> dict:
    """
    验证 JWT token，用于 WebSocket 连接鉴权。
    WebSocket 不支持 Authorization header，通过 query param ?token=xxx 传入。
    """
    if not token or not settings.jwt_secret_key:
        return {"sub": "dev"}
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        raise WebSocketDisconnect(code=4001, reason="Invalid or expired token")


logger = logging.getLogger(__name__)


@router.websocket("/ws/pty")
async def pty_endpoint(websocket: WebSocket, token: str = Query("")):
    """
    PTY WebSocket 端点。

    Linux/容器：使用 ptyprocess 创建真实 PTY
    Windows 开发：使用 asyncio.subprocess 降级（支持交互式 cmd.exe）

    协议：
    - 普通文本消息 → 写入 stdin
    - JSON {"type":"resize","cols":80,"rows":24} → 调整窗口大小 (仅 PTY 模式)
    - 输出 → 以文本发回前端
    - finally 块确保进程被清理
    """
    try:
        await verify_token(token)
    except Exception as e:
        logger.warning(f"PTY token verification failed: {e}, continuing anyway")

    await websocket.accept()

    try:
        if sys.platform == "win32" or ptyprocess is None:
            await _run_windows_shell(websocket)
        else:
            await _run_unix_pty(websocket)
    except Exception as e:
        logger.error(f"PTY handler error: {type(e).__name__}: {e}", exc_info=True)
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(f"\r\n\x1b[31mError: {e}\x1b[0m\r\n")


async def _run_windows_shell(websocket: WebSocket):
    """Windows 开发环境：使用 asyncio.subprocess + cmd.exe 降级方案"""
    import subprocess as _sp
    import os as _os

    # 先发送开发模式提示
    await websocket.send_text(
        "\x1b[33m[开发模式] 当前运行在 Windows 主机，终端连接到本机 cmd.exe\r\n"
        "正式部署时，Docker 容器内将使用 /bin/bash PTY\x1b[0m\r\n\r\n"
    )

    # 使用 cmd.exe /K chcp 65001 强制 UTF-8 输出编码
    env = _os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    proc = await asyncio.create_subprocess_exec(
        "cmd.exe", "/K", "chcp 65001 >nul",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
        creationflags=_sp.CREATE_NO_WINDOW,
    )

    async def read_output():
        """stdout → WebSocket"""
        assert proc.stdout is not None
        while True:
            try:
                data = await proc.stdout.read(4096)
                if not data:
                    break
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
            except Exception:
                break

    async def write_input():
        """WebSocket → stdin"""
        assert proc.stdin is not None
        while True:
            try:
                message = await websocket.receive()

                if "text" in message and message["text"]:
                    raw = message["text"]
                    # 跳过 resize 命令（Windows subprocess 不支持）
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict) and parsed.get("type") == "resize":
                            continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                    proc.stdin.write(raw.encode("utf-8"))
                    await proc.stdin.drain()

                elif "bytes" in message and message["bytes"]:
                    proc.stdin.write(message["bytes"])
                    await proc.stdin.drain()

            except WebSocketDisconnect:
                break
            except Exception:
                break

    try:
        await asyncio.gather(read_output(), write_input())
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


async def _run_unix_pty(websocket: WebSocket):
    """Linux/容器：真实 PTY 模式"""
    proc = ptyprocess.PtyProcess.spawn(
        ["/bin/bash"],
        env={
            "TERM": "xterm-256color",
            "HOME": "/root",
            "PATH": "/opt/miniforge/bin:/usr/local/sbin:/usr/local/bin:"
                    "/usr/sbin:/usr/bin:/sbin:/bin",
        },
    )

    # 发送一个换行触发 bash 提示符显示
    proc.write(b"\n")

    async def read_from_pty():
        """PTY stdout → WebSocket (非阻塞循环读取)"""
        loop = asyncio.get_event_loop()
        while proc.isalive():
            try:
                data = await loop.run_in_executor(None, proc.read, 4096)
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_bytes(data)
            except EOFError:
                break
            except Exception:
                break

    async def write_to_pty():
        """WebSocket → PTY stdin (支持 resize JSON 协议)"""
        while True:
            try:
                message = await websocket.receive()

                if "text" in message and message["text"]:
                    raw = message["text"]
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict) and parsed.get("type") == "resize":
                            rows = int(parsed.get("rows", 24))
                            cols = int(parsed.get("cols", 80))
                            proc.setwinsize(rows, cols)
                            continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                    proc.write(raw.encode("utf-8"))

                elif "bytes" in message and message["bytes"]:
                    proc.write(message["bytes"])

            except WebSocketDisconnect:
                break
            except Exception:
                break

    try:
        await asyncio.gather(read_from_pty(), write_to_pty())
    finally:
        if proc.isalive():
            proc.terminate(force=True)
