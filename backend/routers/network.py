import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import SetupState
from backend.dependencies import get_current_user, get_db  # get_current_user used by /status
from backend.services.singbox_manager import SingboxManager, get_fallback_outbound
from backend.services.subscription_parser import SubscriptionParser

log = logging.getLogger(__name__)

router = APIRouter(tags=["Network"])

manager = SingboxManager()
parser = SubscriptionParser()


class NetworkConfigDTO(BaseModel):
    subscriptionUrl: Optional[str] = None
    useChinaDirect: bool = True


class SubscriptionDTO(BaseModel):
    url: str


@router.post("/api/v1/network/apply")
async def apply_network_config(
    dto: NetworkConfigDTO,
    db: AsyncSession = Depends(get_db),
):
    """应用网络订阅配置并重启 Sing-box"""
    try:
        nodes = []
        if dto.subscriptionUrl:
            try:
                # 获取用户节点
                nodes = await parser.fetch_and_parse(dto.subscriptionUrl)
            except Exception as e:
                # Task 4.2 容灾降级：拉取失败时（超时/被墙），仅记录告警不抛异常。
                # nodes 保持为空数组，后续配置生成将仅使用 fallback_node。
                log.warning(f"Failed to fetch subscription, falling back to built-in node: {e}")
        
        # 获取系统兜底节点
        fallback_node = get_fallback_outbound()
        
        # 组装 config.json
        config = parser.build_singbox_config(
            nodes=nodes,
            fallback_node=fallback_node,
            dns_china_direct=dto.useChinaDirect
        )
        
        # 应用并重启由于禁止降级，抛出的任何异常(比如supervisorctl找不到)都会直接引发500
        await manager.apply_config(config)

        # 更新数据库状态
        result = await db.execute(select(SetupState))
        state = result.scalars().first()
        if not state:
            state = SetupState()
            db.add(state)
        state.network_configured = True
        state.current_step = max(state.current_step or 0, 2)
        await db.commit()

        return {"message": "Network configuration applied successfully"}

    except Exception as e:
        log.exception("Failed to apply network config")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/network/status")
async def get_network_status(current_user = Depends(get_current_user)):
    """获取 Sing-box 进程状态"""
    try:
        status_str = await manager.get_status()
        return {"status": status_str}
    except Exception as e:
        log.exception("Failed to get network status")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/network/test-subscription")
async def test_subscription(
    dto: SubscriptionDTO,
):
    """测试解析订阅链接并返回节点数"""
    try:
        nodes = await parser.fetch_and_parse(dto.url)
        return {
            "success": True, 
            "nodeCount": len(nodes),
            "message": f"Successfully parsed {len(nodes)} nodes"
        }
    except Exception as e:
        log.exception("Failed to test subscription")
        raise HTTPException(
            status_code=500, 
            detail=f"测速失败: {str(e)}。您可以直接点击下一步，系统将自动使用内置兜底节点。"
        )


@router.get("/api/v1/setup/state")
async def get_setup_state(db: AsyncSession = Depends(get_db)):
    """获取向导安装状态，前端初始化时调用"""
    try:
        result = await db.execute(select(SetupState))
        state = result.scalars().first()
        if not state:
            return {
                "is_completed": False,
                "current_step": 0,
                "network_configured": False,
                "llm_configured": False
            }
        return {
            "is_completed": state.is_completed,
            "current_step": state.current_step,
            "network_configured": state.network_configured,
            "llm_configured": state.llm_configured
        }
    except Exception as e:
        log.exception("Failed to get setup state")
        raise HTTPException(status_code=500, detail=str(e))

