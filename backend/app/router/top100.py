"""成交额前100 API"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StockTop100

router = APIRouter(tags=["成交额前100"])


@router.get("/top100")
def get_top100(
    dt: date | None = Query(None, alias="date", description="交易日期，默认返回最新"),
    db: Session = Depends(get_db),
):
    """查询成交额前100股票列表"""
    if dt is None:
        # 默认最新日期
        row = (
            db.query(StockTop100.trade_date)
            .order_by(StockTop100.trade_date.desc())
            .first()
        )
        if row is None:
            return {"date": None, "data": []}
        dt = row.trade_date

    rows = (
        db.query(StockTop100)
        .filter(StockTop100.trade_date == dt)
        .order_by(StockTop100.rank)
        .all()
    )

    return {
        "date": dt.isoformat(),
        "data": [
            {
                "rank": r.rank,
                "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "amount": float(r.amount) if r.amount else None,
                "pct_change": float(r.pct_change) if r.pct_change else None,
                "close": float(r.close) if r.close else None,
            }
            for r in rows
        ],
    }
