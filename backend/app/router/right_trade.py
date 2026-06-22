"""右侧交易 API"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StockDailyRaw
from app.service.right_trade import compute_right_trade

router = APIRouter(tags=["右侧交易"])


@router.get("/right_trade")
def get_right_trade(
    dt: date | None = Query(None, alias="date", description="交易日期，默认返回最新"),
    days: int = Query(10, ge=5, le=60, description="统计周期（交易日天数）"),
    db: Session = Depends(get_db),
):
    """筛选右侧交易标的 — 近N天从低点反弹>15%且未跌破起涨点"""
    if dt is None:
        row = (
            db.query(StockDailyRaw.trade_date)
            .order_by(StockDailyRaw.trade_date.desc())
            .first()
        )
        if row is None:
            return {"date": None, "days": days, "data": []}
        dt = row.trade_date

    data = compute_right_trade(db, dt, days)

    return {
        "date": dt.isoformat(),
        "days": days,
        "data": data,
    }
