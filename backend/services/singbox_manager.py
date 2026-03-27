# backend/services/singbox_manager.py — Sing-box 配置生成 + 进程控制
# 按白皮书 §5.1 陷阱二/三实现
# Task 2.1: parse_vless_uri() + get_fallback_outbound()
# Task 2.2: SingboxManager 类 + _supervisorctl() 函数

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import aiofiles

from backend.config import settings

CONFIG_PATH = Path("/app/config/singbox.json")


def parse_vless_uri(uri: str) -> dict:
    """
    将标准 VLESS share-link URI 解析为 sing-box outbound 字典。

    支持传输层: tcp / h2 / ws / grpc
    支持安全层: reality / tls / none

    示例 URI:
      vless://b32fc64c-8b6e-4fe7-9710-ab181cbc550f@23.27.134.79:48782
              ?encryption=none&security=reality&flow=&type=h2
              &sni=dash.cloudflare.com
              &pbk=RokFzFe0TXFXNr-mdGGf2QNEebOKBrw-IwfLOEw6yn8
              &fp=chrome#USA
    """
    parsed = urlparse(uri)
    if parsed.scheme != "vless":
        raise ValueError(f"仅支持 vless:// URI，收到: {parsed.scheme}://")

    uuid = parsed.username
    host = parsed.hostname
    port = parsed.port
    tag = unquote(parsed.fragment) if parsed.fragment else "fallback"
    qs = parse_qs(parsed.query)

    def q(key: str, default: str = "") -> str:
        return qs.get(key, [default])[0]

    security = q("security")             # reality / tls / none
    sni = q("sni")
    public_key = q("pbk")
    short_id = q("sid", "")
    fingerprint = q("fp", "chrome")      # 必须为 chrome，不能用 random
    flow = q("flow", "")
    network = q("type", "tcp")           # h2 / tcp / ws / grpc

    outbound: dict = {
        "type": "vless",
        "tag": tag,
        "server": host,
        "server_port": port,
        "uuid": uuid,
    }

    if flow:
        outbound["flow"] = flow

    # 传输层配置
    if network == "h2":
        outbound["transport"] = {"type": "http"}
    elif network == "ws":
        outbound["transport"] = {"type": "websocket", "path": q("path", "/")}
    elif network == "grpc":
        outbound["transport"] = {"type": "grpc", "service_name": q("serviceName", "")}
    # tcp 不需要 transport 字段

    # TLS / REALITY 安全层
    if security == "reality":
        outbound["tls"] = {
            "enabled": True,
            "server_name": sni,
            "utls": {"enabled": True, "fingerprint": fingerprint},
            "reality": {
                "enabled": True,
                "public_key": public_key,
                "short_id": short_id,
            },
        }
    elif security == "tls":
        outbound["tls"] = {
            "enabled": True,
            "server_name": sni,
            "utls": {"enabled": True, "fingerprint": fingerprint},
        }

    return outbound


def get_fallback_outbound() -> dict | None:
    """
    从 SINGBOX_FALLBACK_URI 读取兜底节点。
    开源版不强制要求，URI 为空时返回 None。
    """
    uri = settings.singbox_fallback_uri
    if not uri:
        return None
    return parse_vless_uri(uri)


# ── Task 2.2: 进程控制层 ─────────────────────────────────


async def _supervisorctl(*args: str, capture: bool = False) -> str:
    """
    supervisorctl 命令封装，替代 XML-RPC。
    supervisorctl 通过 /var/run/supervisor.sock 通信，容器内 root 直接可用。

    用法:
        await _supervisorctl("restart", "singbox")
        await _supervisorctl("start", "openclaw")
        status = await _supervisorctl("status", "openclaw", capture=True)
    """
    cmd = ["supervisorctl"] + list(args)
    stdout_pipe = asyncio.subprocess.PIPE if capture else asyncio.subprocess.DEVNULL

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=stdout_pipe,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)

    action = args[0] if args else ""
    # stop 允许任何退出码（进程可能 FATAL / STOPPED / 不存在）
    # status 也允许非零（进程未运行）
    # start/restart 失败才抛异常
    if proc.returncode != 0 and action not in ("stop", "status"):
        raise RuntimeError(
            f"supervisorctl {' '.join(args)} 失败 "
            f"(exit {proc.returncode}): {stderr.decode().strip()}"
        )
    return stdout.decode().strip() if capture else ""


class SingboxManager:
    """Sing-box 配置管理 + 进程控制"""

    async def apply_config(self, config: dict) -> None:
        """写入配置 → sing-box 格式校验 → 原子替换 → supervisorctl restart"""
        tmp_path = str(CONFIG_PATH) + ".tmp"

        async with aiofiles.open(tmp_path, "w") as f:
            await f.write(json.dumps(config, ensure_ascii=False, indent=2))

        # 校验：失败时删除 tmp，不影响现有运行配置
        proc = await asyncio.create_subprocess_exec(
            "sing-box", "check", "-c", tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            os.unlink(tmp_path)
            raise ValueError(f"sing-box config 校验失败: {stderr.decode()}")

        os.rename(tmp_path, str(CONFIG_PATH))  # 原子替换
        # 先 stop（进程可能已 FATAL/STOPPED，忽略错误），再 start
        try:
            await _supervisorctl("stop", "singbox")
        except RuntimeError:
            pass  # FATAL / STOPPED 状态下 stop 会失败，可忽略
        await _supervisorctl("start", "singbox")

    async def get_status(self) -> str:
        """查询 sing-box 进程状态，返回 RUNNING / STOPPED / UNKNOWN 等"""
        result = await _supervisorctl("status", "singbox", capture=True)
        parts = result.split()
        return parts[1] if len(parts) >= 2 else "UNKNOWN"
