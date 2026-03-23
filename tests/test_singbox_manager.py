# tests/test_singbox_manager.py — Task 2.2 验收测试
# 使用 mock 模拟 subprocess 和文件 I/O，不依赖容器环境

import asyncio
import json
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.singbox_manager import _supervisorctl, SingboxManager, CONFIG_PATH


# ── 辅助：构造 mock subprocess ──────────────────────────


def _make_mock_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
    """构造一个 mock 的 asyncio.subprocess.Process"""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


# ── 测试 _supervisorctl() ───────────────────────────────


class TestSupervisorctl:
    """_supervisorctl() 命令行封装测试"""

    @pytest.mark.asyncio
    async def test_basic_call(self):
        """正常调用：传入 args 正确组装命令"""
        mock_proc = _make_mock_proc(returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await _supervisorctl("restart", "singbox")

            mock_exec.assert_called_once_with(
                "supervisorctl", "restart", "singbox",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

    @pytest.mark.asyncio
    async def test_capture_stdout(self):
        """capture=True 时返回 stdout 内容"""
        mock_proc = _make_mock_proc(
            returncode=0,
            stdout=b"singbox                          RUNNING   pid 123, uptime 0:05:30",
        )
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _supervisorctl("status", "singbox", capture=True)
            assert "RUNNING" in result
            assert "singbox" in result

    @pytest.mark.asyncio
    async def test_exit_code_3_accepted(self):
        """exit code 3（program not running）视为正常"""
        mock_proc = _make_mock_proc(returncode=3, stderr=b"singbox: NOT_RUNNING")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            # 不应抛出异常
            await _supervisorctl("stop", "singbox")

    @pytest.mark.asyncio
    async def test_nonzero_exit_raises(self):
        """非 0/3 的 exit code 抛出 RuntimeError"""
        mock_proc = _make_mock_proc(returncode=1, stderr=b"unix:///var/run/supervisor.sock refused")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="supervisorctl restart singbox 失败"):
                await _supervisorctl("restart", "singbox")

    @pytest.mark.asyncio
    async def test_no_capture_returns_empty(self):
        """capture=False 时返回空字符串"""
        mock_proc = _make_mock_proc(returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _supervisorctl("restart", "singbox")
            assert result == ""


# ── 测试 SingboxManager ────────────────────────────────


VALID_CONFIG = {
    "log": {"level": "warn"},
    "inbounds": [{"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 2080}],
    "outbounds": [{"type": "direct", "tag": "direct"}],
}


class TestSingboxManagerApplyConfig:
    """SingboxManager.apply_config() 测试"""

    @pytest.mark.asyncio
    async def test_apply_valid_config(self, tmp_path):
        """合法 config：write → check pass → rename → restart"""
        # 使用 tmp_path 模拟 CONFIG_PATH
        config_file = tmp_path / "singbox.json"
        tmp_file = str(config_file) + ".tmp"

        # sing-box check 通过
        check_proc = _make_mock_proc(returncode=0, stderr=b"")
        # supervisorctl restart 通过
        restart_proc = _make_mock_proc(returncode=0)

        manager = SingboxManager()

        with patch.object(
            type(manager), "apply_config",
            wraps=manager.apply_config,
        ):
            with patch(
                "backend.services.singbox_manager.CONFIG_PATH", config_file
            ):
                call_count = {"exec": 0}

                async def mock_create_subprocess(*args, **kwargs):
                    call_count["exec"] += 1
                    if "sing-box" in args:
                        return check_proc
                    return restart_proc

                with patch(
                    "asyncio.create_subprocess_exec",
                    side_effect=mock_create_subprocess,
                ):
                    await manager.apply_config(VALID_CONFIG)

        # 验证最终文件存在且内容正确
        assert config_file.exists()
        with open(config_file) as f:
            written = json.load(f)
        assert written == VALID_CONFIG

        # tmp 文件应已被 rename 消除
        assert not os.path.exists(tmp_file)

    @pytest.mark.asyncio
    async def test_apply_invalid_config(self, tmp_path):
        """非法 config：check 失败 → 删除 tmp → 抛 ValueError → 原文件不变"""
        config_file = tmp_path / "singbox.json"
        tmp_file_path = str(config_file) + ".tmp"

        # 预写入一份"原有正常配置"
        original = {"log": {"level": "info"}, "outbounds": []}
        with open(config_file, "w") as f:
            json.dump(original, f)

        # sing-box check 失败
        check_proc = _make_mock_proc(returncode=1, stderr=b"missing inbounds field")

        manager = SingboxManager()

        with patch("backend.services.singbox_manager.CONFIG_PATH", config_file):
            with patch(
                "asyncio.create_subprocess_exec",
                return_value=check_proc,
            ):
                with pytest.raises(ValueError, match="sing-box config 校验失败"):
                    await manager.apply_config({"bad": "config"})

        # 原配置文件未被修改
        with open(config_file) as f:
            assert json.load(f) == original

        # tmp 文件已被删除
        assert not os.path.exists(tmp_file_path)


class TestSingboxManagerGetStatus:
    """SingboxManager.get_status() 测试"""

    @pytest.mark.asyncio
    async def test_running_status(self):
        """解析 RUNNING 状态"""
        mock_proc = _make_mock_proc(
            returncode=0,
            stdout=b"singbox                          RUNNING   pid 456, uptime 1:23:45",
        )
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            manager = SingboxManager()
            status = await manager.get_status()
            assert status == "RUNNING"

    @pytest.mark.asyncio
    async def test_stopped_status(self):
        """解析 STOPPED 状态"""
        mock_proc = _make_mock_proc(
            returncode=3,
            stdout=b"singbox                          STOPPED   Mar 13 02:30 PM",
        )
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            manager = SingboxManager()
            status = await manager.get_status()
            assert status == "STOPPED"

    @pytest.mark.asyncio
    async def test_empty_output_returns_unknown(self):
        """空输出返回 UNKNOWN"""
        mock_proc = _make_mock_proc(returncode=0, stdout=b"")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            manager = SingboxManager()
            status = await manager.get_status()
            assert status == "UNKNOWN"
