"""成交额前100股票服务"""

import logging
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.models import StockTop100, StockDailyRaw

logger = logging.getLogger(__name__)


def compute_top100(db: Session, trade_date: date) -> int:
    """从原始数据按成交额排序，取前100存入 stock_top100 表

    Args:
        db: 数据库会话
        trade_date: 交易日期

    Returns:
        实际存入的股票数量
    """
    # 查询当日所有股票，按成交额降序
    rows = (
        db.query(StockDailyRaw)
        .filter(StockDailyRaw.trade_date == trade_date)
        .order_by(StockDailyRaw.amount.desc().nullslast())
        .limit(100)
        .all()
    )

    if not rows:
        logger.warning(f"{trade_date} 无成交数据，无法生成 top100")
        return 0

    # 清除当日旧数据（幂等）
    db.execute(
        delete(StockTop100).where(StockTop100.trade_date == trade_date)
    )

    # 批量插入
    records = []
    for rank, row in enumerate(rows, start=1):
        records.append(
            StockTop100(
                trade_date=trade_date,
                rank=rank,
                stock_code=row.stock_code,
                stock_name=row.stock_name,
                amount=row.amount,
                pct_change=row.pct_change,
                close=row.close,
            )
        )

    db.add_all(records)
    db.commit()
    logger.info(f"{trade_date} top100 已生成，共 {len(records)} 条")
    return len(records)
