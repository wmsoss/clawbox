# backend/database.py — 异步数据库引擎 + WAL 配置
# 按白皮书 §5.3 实现：WAL pragma 通过事件钩子注入每个新连接

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

import os

# 容器内使用 /app/db/dalongxia.sqlite，Windows 开发环境使用项目根目录
if os.environ.get("DATABASE_URL"):
    DATABASE_URL = os.environ["DATABASE_URL"]
elif os.name == "nt":
    # Windows 开发环境
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATABASE_URL = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'dalongxia.sqlite'}"
else:
    # 容器内
    DATABASE_URL = "sqlite+aiosqlite:////app/db/dalongxia.sqlite"

# ⚠️ 必须加 connect_args，否则 Uvicorn 多 worker 间会文件锁死
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


# ✅ 正确做法：通过 engine sync_engine 的事件钩子，对每个新连接注入 WAL
@event.listens_for(engine.sync_engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")   # WAL 模式下 NORMAL 足够安全且更快
    cursor.execute("PRAGMA busy_timeout=5000;")    # 等待锁最多 5 秒，避免立刻报错
    cursor.close()


AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """应用启动时调用，创建表结构"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
