"""缠论 API"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StockDailyRaw
from app.service.chan_theory import compute_chan_theory

router = APIRouter(tags=["缠论"])


@router.get("/chan_theory")
def get_chan_theory(
    dt: date | None = Query(None, alias="date", description="交易日期，默认返回最新"),
    db: Session = Depends(get_db),
):
    """缠论1买、2买检测"""
    if dt is None:
        row = (
            db.query(StockDailyRaw.trade_date)
            .order_by(StockDailyRaw.trade_date.desc())
            .first()
        )
        if row is None:
            return {"date": None, "buy1": [], "buy2": []}
        dt = row.trade_date

    data = compute_chan_theory(db, dt)
    data["date"] = dt.isoformat()
    return data
