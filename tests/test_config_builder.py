# tests/test_config_builder.py — Task 2.3 验收测试
# 4 个验收场景：嵌套合并 / __user_locked__ / 列表替换 / bailian DTO 集成

import json
import os
import sys
import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.config_builder import (
    deep_merge,
    load_current_config,
    save_config,
    build_and_apply,
    USER_LOCKED_KEY,
    PROVIDER_CONFIGS,
    CONFIG_PATH,
)
from backend.schemas import LLMConfigDTO


# ── 验收场景 1：嵌套合并不破坏未修改的同级字段 ────────


class TestDeepMergeNested:
    """深度合并不会丢失 base 中未被 override 涉及的字段"""

    def test_sibling_fields_preserved(self):
        base = {
            "models": {
                "mode": "merge",
                "providers": {
                    "openai": {"baseUrl": "https://api.openai.com/v1", "apiKey": "sk-old"},
                    "deepseek": {"baseUrl": "https://api.deepseek.com/v1", "apiKey": "sk-ds"},
                },
            },
            "agents": {"defaults": {"timeout": 30}},
        }
        override = {
            "models": {
                "providers": {
                    "openai": {"apiKey": "sk-new"},  # 只改 apiKey
                },
            },
        }
        result = deep_merge(base, override)

        # openai 的 baseUrl 保留
        assert result["models"]["providers"]["openai"]["baseUrl"] == "https://api.openai.com/v1"
        # openai 的 apiKey 更新
        assert result["models"]["providers"]["openai"]["apiKey"] == "sk-new"
        # deepseek 完全不受影响
        assert result["models"]["providers"]["deepseek"]["apiKey"] == "sk-ds"
        # mode 字段保留
        assert result["models"]["mode"] == "merge"
        # agents.defaults.timeout 保留
        assert result["agents"]["defaults"]["timeout"] == 30

    def test_new_key_added(self):
        """override 引入新 key 时正确添加"""
        base = {"a": 1}
        override = {"b": 2}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_deep_nesting(self):
        """多层嵌套合并"""
        base = {"l1": {"l2": {"l3": {"keep": True, "old": "val"}}}}
        override = {"l1": {"l2": {"l3": {"new": "added"}}}}
        result = deep_merge(base, override)
        assert result["l1"]["l2"]["l3"]["keep"] is True
        assert result["l1"]["l2"]["l3"]["old"] == "val"
        assert result["l1"]["l2"]["l3"]["new"] == "added"


# ── 验收场景 2：__user_locked__ 标记阻止覆写 ──────────


class TestDeepMergeUserLocked:
    """带 __user_locked__=True 的子树不被 override 覆写"""

    def test_locked_node_not_overwritten(self):
        base = {
            "models": {
                "providers": {
                    "custom": {
                        USER_LOCKED_KEY: True,
                        "baseUrl": "https://my-custom-api.com/v1",
                        "apiKey": "user-key",
                    }
                }
            }
        }
        override = {
            "models": {
                "providers": {
                    "custom": {
                        "baseUrl": "https://override-attempt.com/v1",
                        "apiKey": "override-key",
                    }
                }
            }
        }
        result = deep_merge(base, override)

        # custom 节点被锁定，保留用户原始值
        assert result["models"]["providers"]["custom"]["baseUrl"] == "https://my-custom-api.com/v1"
        assert result["models"]["providers"]["custom"]["apiKey"] == "user-key"

    def test_unlocked_sibling_still_merged(self):
        """锁定的节点旁边的未锁定节点仍正常合并"""
        base = {
            "providers": {
                "locked_one": {USER_LOCKED_KEY: True, "val": "original"},
                "open_one": {"val": "old"},
            }
        }
        override = {
            "providers": {
                "locked_one": {"val": "attempt"},
                "open_one": {"val": "new"},
            }
        }
        result = deep_merge(base, override)
        assert result["providers"]["locked_one"]["val"] == "original"
        assert result["providers"]["open_one"]["val"] == "new"


# ── 验收场景 3：列表字段整体替换 ──────────────────────


class TestDeepMergeListReplace:
    """列表类型字段：override 完全替换 base（不做列表合并/追加）"""

    def test_list_replaced_not_appended(self):
        base = {
            "models": {
                "providers": {
                    "openai": {
                        "models": [
                            {"id": "gpt-4o", "name": "gpt-4o"},
                        ]
                    }
                }
            }
        }
        override = {
            "models": {
                "providers": {
                    "openai": {
                        "models": [
                            {"id": "gpt-4o-mini", "name": "gpt-4o-mini"},
                        ]
                    }
                }
            }
        }
        result = deep_merge(base, override)

        models_list = result["models"]["providers"]["openai"]["models"]
        # 列表被完全替换，长度为 1，只有新值
        assert len(models_list) == 1
        assert models_list[0]["id"] == "gpt-4o-mini"

    def test_list_to_list_no_merge(self):
        """简单列表替换"""
        base = {"tags": ["a", "b", "c"]}
        override = {"tags": ["x", "y"]}
        result = deep_merge(base, override)
        assert result["tags"] == ["x", "y"]


# ── 验收场景 4：bailian DTO 集成测试 ─────────────────


class TestBuildAndApply:
    """提交 bailian DTO 后 openclaw.json 正确生成"""

    @pytest.mark.asyncio
    async def test_bailian_dto_integration(self, tmp_path):
        """集成测试：bailian/qwen3.5-plus DTO → 正确的 openclaw.json"""
        config_file = tmp_path / "openclaw.json"

        dto = LLMConfigDTO(
            provider="bailian",
            model_name="qwen3.5-plus",
            api_key="sk-test-bailian-key",
        )

        from unittest.mock import patch as mock_patch

        with mock_patch("backend.services.config_builder.CONFIG_PATH", config_file):
            await build_and_apply(dto)

        # 读取生成的文件
        with open(config_file) as f:
            result = json.load(f)

        # 验证 agents.defaults.model.primary
        assert result["agents"]["defaults"]["model"]["primary"] == "bailian/qwen3.5-plus"

        # 验证 provider 配置
        provider = result["models"]["providers"]["bailian"]
        assert provider["baseUrl"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert provider["apiKey"] == "sk-test-bailian-key"
        assert provider["api"] == "openai-completions"

        # 验证 model entry
        models = provider["models"]
        assert len(models) == 1
        assert models[0]["id"] == "qwen3.5-plus"
        assert models[0]["contextWindow"] == 1000000
        assert models[0]["compat"]["thinkingFormat"] == "qwen"

        # 验证空骨架字段保留
        assert result["models"]["mode"] == "merge"

    @pytest.mark.asyncio
    async def test_custom_provider_uses_custom_url(self, tmp_path):
        """custom 提供商使用用户填写的 base_url"""
        config_file = tmp_path / "openclaw.json"

        dto = LLMConfigDTO(
            provider="custom",
            model_name="my-model",
            api_key="sk-custom",
            custom_base_url="https://my-api.example.com/v1",
        )

        from unittest.mock import patch as mock_patch

        with mock_patch("backend.services.config_builder.CONFIG_PATH", config_file):
            await build_and_apply(dto)

        with open(config_file) as f:
            result = json.load(f)

        assert result["models"]["providers"]["custom"]["baseUrl"] == "https://my-api.example.com/v1"
        assert result["agents"]["defaults"]["model"]["primary"] == "custom/my-model"

    @pytest.mark.asyncio
    async def test_merge_preserves_existing_providers(self, tmp_path):
        """第二次配置不会删除第一次配置的 provider"""
        config_file = tmp_path / "openclaw.json"

        from unittest.mock import patch as mock_patch

        # 第一次：配置 openai
        dto1 = LLMConfigDTO(provider="openai", model_name="gpt-4o", api_key="sk-openai")
        with mock_patch("backend.services.config_builder.CONFIG_PATH", config_file):
            await build_and_apply(dto1)

        # 第二次：配置 bailian
        dto2 = LLMConfigDTO(provider="bailian", model_name="qwen3-max", api_key="sk-bailian")
        with mock_patch("backend.services.config_builder.CONFIG_PATH", config_file):
            await build_and_apply(dto2)

        with open(config_file) as f:
            result = json.load(f)

        # 两个 provider 都存在
        assert "openai" in result["models"]["providers"]
        assert "bailian" in result["models"]["providers"]
        # primary 更新为最后配置的
        assert result["agents"]["defaults"]["model"]["primary"] == "bailian/qwen3-max"
