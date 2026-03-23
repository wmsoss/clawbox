from datetime import datetime, timedelta, timezone
import logging
import subprocess
import sys as _sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import AdminUser, SetupState
from backend.dependencies import get_db, get_current_user
from backend.schemas import ResetSystemRequest

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# JWT Configuration
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRegister(BaseModel):
    username: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    if not SECRET_KEY:
        log.error("JWT_SECRET_KEY is not configured in .env")
        raise HTTPException(status_code=500, detail="JWT secret key is missing")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def sync_password_to_openclaw(password: str) -> bool:
    """将密码同步到 OpenClaw gateway.auth 配置（直接读写 JSON 文件）

    后端运行在容器内部，直接操作 /app/config/openclaw.json。
    同时设置 auth.mode = "password" 和 auth.password = <密码>。
    """
    import json
    config_path = "/app/config/openclaw.json"
    # Windows 开发环境兼容
    if _sys.platform == "win32":
        config_path = str(Path(__file__).resolve().parent.parent.parent / "openclaw.json")

    try:
        # 读取现有配置
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 更新 gateway.auth 节点
        config.setdefault("gateway", {}).setdefault("auth", {})
        config["gateway"]["auth"]["mode"] = "password"
        config["gateway"]["auth"]["password"] = password
        # 清理旧的 token 字段和不兼容的 key（曾错误放在 auth 下）
        config["gateway"]["auth"].pop("token", None)
        config["gateway"]["auth"].pop("dangerouslyDisableDeviceAuth", None)

        # 确保 controlUi 设备配对和 HTTP 认证正确（本地部署必需）
        config["gateway"].setdefault("controlUi", {})
        config["gateway"]["controlUi"]["dangerouslyDisableDeviceAuth"] = True
        config["gateway"]["controlUi"]["allowInsecureAuth"] = True

        # 原子写入
        tmp_path = config_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        import os as _os
        _os.replace(tmp_path, config_path)

        log.info("Password synced to OpenClaw config (direct file write)")
        return True
    except FileNotFoundError:
        log.warning(f"OpenClaw config not found: {config_path}, skip sync")
        return False
    except Exception as e:
        log.warning(f"Error syncing password to OpenClaw: {e}")
        return False


@router.get("/check-user-exists")
async def check_user_exists(db: AsyncSession = Depends(get_db)):
    """检查是否存在管理员用户（公开接口，前端路由守卫调用）"""
    result = await db.execute(select(AdminUser))
    user = result.scalars().first()
    return {"exists": user is not None}


@router.post("/register", response_model=dict)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    """首次注册 Admin (仅当无用户时可用)"""
    result = await db.execute(select(AdminUser))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin user already exists"
        )

    hashed_password = get_password_hash(user.password)
    new_user = AdminUser(username=user.username, password_hash=hashed_password)
    db.add(new_user)
    await db.commit()

    # 同步密码到 OpenClaw
    sync_password_to_openclaw(user.password)

    return {"message": "Admin user created successfully"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """登录获取 JWT token"""
    result = await db.execute(select(AdminUser).where(AdminUser.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


from backend.dependencies import get_current_user

@router.get("/me")
async def read_users_me(current_user: AdminUser = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {"username": current_user.username}

@router.post("/reset-password")
async def reset_password(
    new_password: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """重置当前用户密码（需登录）"""
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少为 6 位"
        )

    hashed_password = get_password_hash(new_password)
    current_user.password_hash = hashed_password
    await db.commit()

    # 同步密码到 OpenClaw
    sync_password_to_openclaw(new_password)

    log.info(f"Password reset for user {current_user.username}")
    return {"message": "密码已重置"}

@router.post("/forgot-password")
async def forgot_password(
    username: str = Body(..., embed=True),
    new_password: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """忘记密码重置（公开接口，通过用户名重置密码）"""
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少为 6 位"
        )

    hashed_password = get_password_hash(new_password)
    user.password_hash = hashed_password
    await db.commit()

    # 同步密码到 OpenClaw
    sync_password_to_openclaw(new_password)

    log.info(f"Password reset via forgot-password for user {username}")
    return {"message": f"用户 '{username}' 的密码已重置为：{new_password}"}

@router.post("/reset-all")
async def reset_all_users(req: ResetSystemRequest, db: AsyncSession = Depends(get_db)):
    """公开接口：清空所有用户 + 设置状态，使系统回到向导页"""
    if req.confirm != "RESET":
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation string"
        )
    
    # 清空用户并重置向导状态，但保留 InstalledSkill
    await db.execute(delete(AdminUser))
    await db.execute(delete(SetupState))
    await db.commit()
    
    log.info("System reset via /reset-all public API")
    return {"message": "All users cleared, redirect to wizard"}
