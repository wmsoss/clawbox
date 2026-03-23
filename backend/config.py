# backend/config.py — 配置管理
# 通过 pydantic-settings 从 .env 读取环境变量

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # 内置凭证
    github_token: str = ""
    clawhub_token: str = ""

    # JWT (无默认值，未设置时启动即报错)
    jwt_secret_key: str = ""

    # 兜底节点：整条 URI 存储，由 parse_vless_uri() 解析
    singbox_fallback_uri: str = ""




settings = Settings()
