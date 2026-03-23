# backend/schemas.py — Pydantic DTO 定义（契约层）
# 按白皮书 §6.2 定义，前后端数据传输的唯一契约

from pydantic import BaseModel, Field
from typing import Literal, Optional


class AdminRegisterDTO(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LLMConfigDTO(BaseModel):
    provider: Literal["openai", "anthropic", "bailian", "deepseek", "gemini", "custom"]
    model_name: str
    api_key: str = Field(min_length=1)
    custom_base_url: Optional[str] = ""


class NetworkConfigDTO(BaseModel):
    subscription_url: Optional[str] = None  # 为空则只用兜底节点


class SkillInstallDTO(BaseModel):
    repo_url: str
    name: str


class SetupStepRequest(BaseModel):
    step: int
    data: dict  # 根据 step 不同，data 结构不同，后端按 step 分发解析


class ResetSystemRequest(BaseModel):
    confirm: Literal["RESET"] = Field(..., description="必须传入 'RESET' 以确认重置操作")
