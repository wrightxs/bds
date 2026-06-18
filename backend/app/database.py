"""数据库引擎和会话管理"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_size=5, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
