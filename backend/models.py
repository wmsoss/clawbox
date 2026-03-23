# backend/models.py — SQLAlchemy ORM 模型
# 按白皮书 §6.1 定义三张表：AdminUser, SetupState, InstalledSkill

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from backend.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SetupState(Base):
    """记录向导完成状态，避免重复初始化"""
    __tablename__ = "setup_state"

    id = Column(Integer, primary_key=True, default=1)  # 单行表
    is_completed = Column(Boolean, default=False)
    current_step = Column(Integer, default=0)
    network_configured = Column(Boolean, default=False)
    llm_configured = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)


class InstalledSkill(Base):
    __tablename__ = "installed_skills"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    repo_url = Column(String(512), nullable=False)
    version = Column(String(64), default="latest")
    install_path = Column(String(512))
    is_active = Column(Boolean, default=True)
    installed_at = Column(DateTime, server_default=func.now())
    last_error = Column(Text, nullable=True)  # 安装失败时记录错误信息
