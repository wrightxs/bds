"""涨停股票 & 仪表盘 & 数据抓取 API"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import delete, func, desc

from app.database import get_db
from app.models import StockDailyRaw, StockLimitUp, StockTop100
from app.service.top100 import compute_top100
from app.service.limit_up import compute_limit_up

logger = logging.getLogger(__name__)

router = APIRouter(tags=["涨停股票"])

# 板块中文映射
BOARD_LABELS = {
    "main": "主板",
    "chi_next": "创业板",
    "star": "科创板",
    "bse": "北交所",
}


@router.get("/limit_up")
def get_limit_up(
    dt: date | None = Query(None, alias="date", description="交易日期，默认返回最新"),
    board: str | None = Query(None, description="板块筛选: main/chi_next/star/bse"),
    db: Session = Depends(get_db),
):
    """查询涨停股票列表，支持按板块筛选"""
    if dt is None:
        row = (
            db.query(StockLimitUp.trade_date)
            .order_by(StockLimitUp.trade_date.desc())
            .first()
        )
        if row is None:
            return {"date": None, "data": []}
        dt = row.trade_date

    q = db.query(StockLimitUp).filter(StockLimitUp.trade_date == dt)
    if board:
        q = q.filter(StockLimitUp.board == board)
    q = q.order_by(StockLimitUp.consecutive.desc(), StockLimitUp.pct_change.desc())

    rows = q.all()

    return {
        "date": dt.isoformat(),
        "data": [
            {
                "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "limit_up_price": float(r.limit_up_price) if r.limit_up_price else None,
                "board": r.board,
                "board_label": BOARD_LABELS.get(r.board, r.board),
                "pct_change": float(r.pct_change) if r.pct_change else None,
                "consecutive": r.consecutive,
            }
            for r in rows
        ],
    }


@router.get("/dashboard")
def get_dashboard(
    dt: date | None = Query(None, alias="date", description="交易日期，默认返回最新"),
    db: Session = Depends(get_db),
):
    """仪表盘摘要数据"""
    if dt is None:
        row = (
            db.query(StockDailyRaw.trade_date)
            .order_by(StockDailyRaw.trade_date.desc())
            .first()
        )
        if row is None:
            return {"date": None, "total_turnover": 0, "limit_up_count": 0, "top_stock": None}
        dt = row.trade_date

    # 总成交额
    total_amount = (
        db.query(func.sum(StockDailyRaw.amount))
        .filter(StockDailyRaw.trade_date == dt)
        .scalar()
    ) or 0

    # 涨停数量
    limit_up_count = (
        db.query(func.count(StockLimitUp.id))
        .filter(StockLimitUp.trade_date == dt)
        .scalar()
    ) or 0

    # 成交额第一的股票
    top_stock_row = (
        db.query(StockTop100)
        .filter(StockTop100.trade_date == dt, StockTop100.rank == 1)
        .first()
    )

    return {
        "date": dt.isoformat(),
        "total_turnover": float(total_amount),
        "stock_count": db.query(func.count(StockDailyRaw.id))
        .filter(StockDailyRaw.trade_date == dt)
        .scalar() or 0,
        "limit_up_count": limit_up_count,
        "top_stock": {
            "stock_code": top_stock_row.stock_code,
            "stock_name": top_stock_row.stock_name,
            "amount": float(top_stock_row.amount) if top_stock_row and top_stock_row.amount else None,
            "pct_change": float(top_stock_row.pct_change) if top_stock_row and top_stock_row.pct_change else None,
        } if top_stock_row else None,
    }


@router.post("/fetch")
def trigger_fetch(
    dt: date | None = Query(None, alias="date", description="抓取日期，默认今天"),
    db: Session = Depends(get_db),
):
    """手动触发数据抓取（也可用于定时任务调用）"""
    from app.fetcher import get_fetcher
    from app.service.top100 import compute_top100
    from app.service.limit_up import compute_limit_up

    if dt is None:
        dt = date.today()

    fetcher = get_fetcher()

    # 1. 从数据源获取原始数据
    try:
        raw_data = fetcher.fetch_daily_data(dt)
    except Exception as e:
        logger.exception(f"数据源获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据源获取失败: {e}")

    if not raw_data:
        raise HTTPException(status_code=404, detail=f"{dt} 无交易数据（可能是非交易日）")

    # 2. 批量写入原始数据（幂等：先删后插）
    db.execute(
        delete(StockDailyRaw).where(StockDailyRaw.trade_date == dt)
    )
    records = [
        StockDailyRaw(
            trade_date=r.get("trade_date", dt),
            stock_code=r["stock_code"],
            stock_name=r["stock_name"],
            open=r.get("open"),
            close=r.get("close"),
            high=r.get("high"),
            low=r.get("low"),
            volume=r.get("volume"),
            amount=r.get("amount"),
            pct_change=r.get("pct_change"),
            turnover_rate=r.get("turnover_rate"),
        )
        for r in raw_data
    ]
    db.add_all(records)
    db.commit()
    logger.info(f"{dt} 原始数据已写入，共 {len(records)} 条")

    # 3. 生成 top100
    top100_count = compute_top100(db, dt)

    # 4. 识别涨停
    limit_up_count = compute_limit_up(db, dt)

    return {
        "date": dt.isoformat(),
        "raw_count": len(records),
        "top100_count": top100_count,
        "limit_up_count": limit_up_count,
    }


@router.get("/dates")
def get_dates(db: Session = Depends(get_db)):
    """查询数据库中已有的交易日期列表"""
    rows = (
        db.query(StockDailyRaw.trade_date)
        .distinct()
        .order_by(desc(StockDailyRaw.trade_date))
        .limit(60)
        .all()
    )
    return {"dates": [r.trade_date.isoformat() for r in rows]}
