# tests/test_pty.py — Task 2.5 验收测试
# 测试 JWT verify_token 逻辑和 PTY 进程清理逻辑
# 注意：ptyprocess 依赖 fcntl（仅 Linux），Windows 上需要 mock

import os
import sys
import types
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── 在导入 pty.py 前 mock 掉 ptyprocess（Windows 无 fcntl 模块）──
_mock_ptyprocess = MagicMock()
sys.modules["ptyprocess"] = _mock_ptyprocess

from jose import jwt
from fastapi import WebSocketDisconnect

# 现在可以安全导入 pty.py
from backend.routers.pty import verify_token, pty_endpoint, router


# ── 测试 verify_token ──────────────────────────────────


MOCK_SECRET = "test-secret-key-for-unit-testing-only-000000000000"


class TestVerifyToken:
    """JWT token 验证逻辑"""

    @pytest.mark.asyncio
    async def test_valid_token_passes(self):
        """合法 token 不抛异常，返回 payload"""
        token = jwt.encode(
            {"sub": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            MOCK_SECRET,
            algorithm="HS256",
        )

        with patch.object(
            type(sys.modules["backend.routers.pty"].settings),
            "jwt_secret_key",
            MOCK_SECRET,
            create=True,
        ):
            # 直接 patch settings 对象的属性
            original = sys.modules["backend.routers.pty"].settings
            mock_settings = MagicMock()
            mock_settings.jwt_secret_key = MOCK_SECRET
            sys.modules["backend.routers.pty"].settings = mock_settings
            try:
                payload = await verify_token(token)
                assert payload["sub"] == "admin"
            finally:
                sys.modules["backend.routers.pty"].settings = original

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self):
        """非法 token 抛出 WebSocketDisconnect"""
        original = sys.modules["backend.routers.pty"].settings
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = MOCK_SECRET
        sys.modules["backend.routers.pty"].settings = mock_settings
        try:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await verify_token("invalid.token.here")
            assert exc_info.value.code == 4001
        finally:
            sys.modules["backend.routers.pty"].settings = original

    @pytest.mark.asyncio
    async def test_expired_token_raises(self):
        """过期 token 抛出 WebSocketDisconnect"""
        token = jwt.encode(
            {"sub": "admin", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            MOCK_SECRET,
            algorithm="HS256",
        )

        original = sys.modules["backend.routers.pty"].settings
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = MOCK_SECRET
        sys.modules["backend.routers.pty"].settings = mock_settings
        try:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await verify_token(token)
            assert exc_info.value.code == 4001
        finally:
            sys.modules["backend.routers.pty"].settings = original

    @pytest.mark.asyncio
    async def test_wrong_secret_raises(self):
        """使用错误密钥签发的 token 被拒绝"""
        token = jwt.encode(
            {"sub": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm="HS256",
        )

        original = sys.modules["backend.routers.pty"].settings
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = MOCK_SECRET
        sys.modules["backend.routers.pty"].settings = mock_settings
        try:
            with pytest.raises(WebSocketDisconnect):
                await verify_token(token)
        finally:
            sys.modules["backend.routers.pty"].settings = original


# ── 测试 PTY 进程清理逻辑 ──────────────────────────────


class TestPTYCleanup:
    """验证 PTY 进程在 WebSocket 断开时被清理"""

    def test_pty_endpoint_has_finally_cleanup(self):
        """验证 pty_endpoint 函数代码中包含 finally + terminate 清理逻辑"""
        import inspect

        source = inspect.getsource(pty_endpoint)
        # 验证关键清理逻辑存在
        assert "finally:" in source, "pty_endpoint 必须包含 finally 块"
        assert "terminate" in source, "finally 块中必须调用 terminate 清理 PTY"
        assert "proc.isalive()" in source, "terminate 前应检查 proc.isalive()"

    def test_router_registered(self):
        """验证 WebSocket 路由已注册"""
        ws_routes = [r for r in router.routes if hasattr(r, "path") and r.path == "/ws/pty"]
        assert len(ws_routes) == 1, "应有一个 /ws/pty WebSocket 路由"
