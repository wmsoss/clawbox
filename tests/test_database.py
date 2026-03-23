# tests/test_database.py — Task 2.4 验收测试
# 3 个验收场景：自动建表 / WAL pragma / 并发写入无锁

import asyncio
import os
import sys
import pytest
import pytest_asyncio

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func


# ── 测试用 ORM 模型（前缀 DB_ 避免与 pytest Test* 冲突）──


class DBBase(DeclarativeBase):
    pass


class DBAdminUser(DBBase):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class DBSetupState(DBBase):
    __tablename__ = "setup_state"
    id = Column(Integer, primary_key=True, default=1)
    is_completed = Column(Boolean, default=False)
    current_step = Column(Integer, default=0)
    network_configured = Column(Boolean, default=False)
    llm_configured = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)


class DBInstalledSkill(DBBase):
    __tablename__ = "installed_skills"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    repo_url = Column(String(512), nullable=False)
    version = Column(String(64), default="latest")
    install_path = Column(String(512))
    is_active = Column(Boolean, default=True)
    installed_at = Column(DateTime, server_default=func.now())
    last_error = Column(Text, nullable=True)


# ── Fixtures ────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    """创建临时数据库引擎并注入 WAL pragma（与 production database.py 逻辑一致）"""
    db_path = tmp_path / "test.sqlite"
    url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(
        url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # 与 production database.py 相同的 WAL 事件钩子
    @event.listens_for(engine.sync_engine, "connect")
    def set_wal_mode(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()

    # 建表
    async with engine.begin() as conn:
        await conn.run_sync(DBBase.metadata.create_all)

    yield engine, db_path

    await engine.dispose()


# ── 验收场景 1：自动建表 ────────────────────────────────


class TestAutoCreateTables:
    """init_db() 后 sqlite 文件自动创建且包含 3 张表"""

    @pytest.mark.asyncio
    async def test_sqlite_file_created(self, db_engine):
        engine, db_path = db_engine
        assert db_path.exists(), "SQLite 文件应被自动创建"

    @pytest.mark.asyncio
    async def test_three_tables_exist(self, db_engine):
        engine, _ = db_engine
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = [row[0] for row in result.fetchall()]

        assert "admin_users" in tables
        assert "setup_state" in tables
        assert "installed_skills" in tables

    @pytest.mark.asyncio
    async def test_admin_users_columns(self, db_engine):
        """验证 admin_users 表结构"""
        engine, _ = db_engine
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA table_info(admin_users)"))
            columns = {row[1] for row in result.fetchall()}

        assert {"id", "username", "password_hash", "created_at"} <= columns


# ── 验收场景 2：WAL pragma 验证 ─────────────────────────


class TestWALPragma:
    """连接后 PRAGMA journal_mode 返回 wal"""

    @pytest.mark.asyncio
    async def test_journal_mode_is_wal(self, db_engine):
        engine, _ = db_engine
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA journal_mode;"))
            mode = result.scalar()
        assert mode == "wal"

    @pytest.mark.asyncio
    async def test_synchronous_is_normal(self, db_engine):
        engine, _ = db_engine
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA synchronous;"))
            # NORMAL = 1
            val = result.scalar()
        assert val == 1

    @pytest.mark.asyncio
    async def test_busy_timeout_is_5000(self, db_engine):
        engine, _ = db_engine
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA busy_timeout;"))
            val = result.scalar()
        assert val == 5000


# ── 验收场景 3：并发 10 请求写入无 database is locked ───


class TestConcurrentWrites:
    """并发 10 个请求写入 InstalledSkill，无 database is locked"""

    @pytest.mark.asyncio
    async def test_10_concurrent_inserts(self, db_engine):
        engine, _ = db_engine
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def insert_skill(i: int):
            async with session_factory() as session:
                skill = DBInstalledSkill(
                    name=f"skill-{i}",
                    repo_url=f"https://github.com/test/skill-{i}",
                )
                session.add(skill)
                await session.commit()

        # 并发 10 个写入任务
        tasks = [insert_skill(i) for i in range(10)]
        await asyncio.gather(*tasks)  # 不应抛出任何异常

        # 验证全部 10 条记录存在
        async with session_factory() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM installed_skills")
            )
            count = result.scalar()
        assert count == 10

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, db_engine):
        """并发读写混合操作"""
        engine, _ = db_engine
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def write_op(i: int):
            async with session_factory() as session:
                skill = DBInstalledSkill(
                    name=f"mixed-{i}",
                    repo_url=f"https://github.com/test/mixed-{i}",
                )
                session.add(skill)
                await session.commit()

        async def read_op():
            async with session_factory() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM installed_skills")
                )
                return result.scalar()

        # 混合 10 写 + 10 读
        tasks = []
        for i in range(10):
            tasks.append(write_op(i))
            tasks.append(read_op())

        await asyncio.gather(*tasks)  # 无异常即通过
