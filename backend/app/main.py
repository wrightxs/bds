"""FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.router import top100, limit_up, right_trade


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化定时任务
    from app.scheduler import start_scheduler

    start_scheduler()
    yield


app = FastAPI(title="BDS - 股票分析系统", lifespan=lifespan)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(top100.router, prefix="/api")
app.include_router(limit_up.router, prefix="/api")
app.include_router(right_trade.router, prefix="/api")


@app.get("/api/health")
def health():
    """健康检查接口"""
    return {"status": "ok"}
