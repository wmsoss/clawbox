# backend/routers/system.py — 系统管理接口
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user, get_db
from backend.models import AdminUser, SetupState, InstalledSkill

log = logging.getLogger(__name__)

router = APIRouter(tags=["System"])


@router.post("/api/v1/system/reset")
async def reset_system(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """清空所有用户数据，重置系统到初始状态（需登录）。
    删除范围：AdminUser + SetupState + InstalledSkill
    保留文件：singbox.json / openclaw.json
    """
    try:
        await db.execute(delete(InstalledSkill))
        await db.execute(delete(SetupState))
        await db.execute(delete(AdminUser))
        await db.commit()
        log.info("System reset by user: %s", current_user.username)
        return {"message": "System reset successfully"}
    except Exception as e:
        log.exception("Failed to reset system")
        raise HTTPException(status_code=500, detail=str(e))
