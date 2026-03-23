from fastapi import APIRouter, Query, HTTPException, Depends
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.schemas import LLMConfigDTO
from backend.models import SetupState
from backend.dependencies import get_current_user, get_db
from backend.services.config_builder import build_and_apply

router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])

@router.get("/models")
async def get_models(
    provider: str = Query(..., description="模型提供商名称"),
    api_key: str = Query(..., description="提供商的 API Key"),
    base_url: Optional[str] = Query(None, description="自定义 Base URL")
):
    """动态拉取各类提供商的可用模型列表。此接口免 JWT 鉴权以供前端初始化阶段使用。"""
    
    if provider == "openai":
        target_base_url = "https://api.openai.com/v1"
    elif provider == "deepseek":
        target_base_url = "https://api.deepseek.com"  # Updated to root, the code appends /models
    elif provider == "bailian":
        target_base_url = base_url or "https://coding.dashscope.aliyuncs.com/v1"
    elif provider == "gemini":
        target_base_url = f"https://generativelanguage.googleapis.com/v1beta"
    else:
        # custom or anthropic
        target_base_url = base_url or ""

    models_list = []

    # 针对百炼 Coding Plan 的拦截写死（因上游不提供动态枚举接口）
    if "coding.dashscope.aliyuncs.com" in (target_base_url or ""):
        return {"models": [
            "qwen3.5-plus", "qwen3-max-2026-01-23", "qwen3-coder-next", "qwen3-coder-plus",
            "glm-5", "glm-4.7", "kimi-k2.5", "MiniMax-M2.5"
        ]}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "anthropic":
                # Anthropic API format
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                url = "https://api.anthropic.com/v1/models"
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                models_list = [item["id"] for item in data.get("data", [])]

            elif provider == "gemini":
                # Google Gemini API format
                url = f"{target_base_url}/models?key={api_key}"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("models", []):
                    # 过滤支持 generateContent 的模型
                    if "generateContent" in item.get("supportedGenerationMethods", []):
                        # 处理前缀：gemini 返回如 "models/gemini-1.5-pro"
                        name = item["name"].replace("models/", "")
                        models_list.append(name)
                        
            else:
                # OpenAI Compatible Format (openai, deepseek, bailian, rjlabs, custom)
                if not target_base_url:
                    raise HTTPException(status_code=400, detail="Custom provider requires base_url")
                
                # Normalize base url, ensure it ends with /models but handles /v1 properly
                url = f"{target_base_url.rstrip('/')}/models"
                if '/v1/models' not in url and not url.endswith('/v1/models') and not url.endswith('/models'):
                    url = f"{target_base_url.rstrip('/')}/v1/models"

                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                # 过滤 embedding, tts, whisper, dall-e
                excludes = ["embedding", "tts", "whisper", "dall-e"]
                for item in data.get("data", []):
                    model_id = item.get("id", "")
                    if not any(ex in model_id.lower() for ex in excludes):
                        models_list.append(model_id)

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch models from provider: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return {"models": models_list}


@router.post("/apply")
async def apply_llm_config(
    dto: LLMConfigDTO,
    db: AsyncSession = Depends(get_db),
):
    """
    接收前端 LLM 配置并通过 build_and_apply 写入 openclaw.json (Deep Merge)。
    仅在向导 Step3 提交时调用。
    """
    # from backend.services.config_builder import build_and_apply # This import is redundant due to global import
    # 利用配置构造器合并配置
    try:
        await build_and_apply(dto)
        
        # 更新 SetupState
        result = await db.execute(select(SetupState))
        state = result.scalars().first()
        if not state:
            state = SetupState()
            db.add(state)
        state.llm_configured = True
        state.current_step = max(state.current_step or 0, 3)
        await db.commit()
        
        return {"status": "ok", "message": "LLM 配置已写入 openclaw.json"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置写入失败: {str(e)}")
