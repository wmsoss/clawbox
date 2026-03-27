# backend/main.py — FastAPI 控制面入口
# Task 1.2 stub: 仅 /health 端点，Sprint 2 将注册所有 router

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.database import init_db
from backend.routers import llm, agent, pty, skills, auth, network, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    yield


app = FastAPI(
    title="大龙虾控制面",
    description="Dalongxia AI Agent Sandbox Control Plane",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(llm.router)
app.include_router(agent.router)
app.include_router(pty.router)
app.include_router(skills.router)
app.include_router(auth.router)
app.include_router(network.router)
app.include_router(system.router)

# CORS — 允许 Tauri WebView 和本地开发访问
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """健康检查端点，供 Docker healthcheck 和前端使用"""
    return {"status": "ok"}

# 挂载前端静态文件
# 容器内唯一路径: /app/static (由 Dockerfile.app 构建写入)
# Windows 开发环境: frontend/dist (本地 npm run build)
import sys as _sys
if _sys.platform != "win32":
    frontend_dist = Path("/app/static")
else:
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # 因为 Vue router 使用 HTML5 History 模式，任何非 /api 且未命中的路径都应该返回 index.html
    @app.get("/{full_path:path}")
    async def serve_vue_app(request: Request, full_path: str):
        # 排除掉 /api、/ws 等后台接口
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return FileResponse(frontend_dist / "index.html", status_code=404)
        
        # 兜底返回主界面，交给 Vue Router 处理
        return FileResponse(frontend_dist / "index.html")
