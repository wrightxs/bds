"""涨停股票识别服务

涨停判断规则：
- 主板（60xxxx, 00xxxx）：涨幅 >= 9.97%
- 创业板（30xxxx）：涨幅 >= 19.97%
- 科创板（68xxxx）：涨幅 >= 19.97%
- 北交所（83xxxx, 43xxxx）：涨幅 >= 29.97%

连板计算：查询最近一个交易日的涨停记录，如果股票再次涨停则连板天数+1。
"""

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session
from sqlalchemy import delete, desc

from app.models import StockLimitUp, StockDailyRaw

logger = logging.getLogger(__name__)

# 各板块涨停阈值（使用 Decimal 精度兜底，但实际比较用浮点+epsilon）
# 前收盘价 * 涨停比例 = 涨停价，收盘价 >= 涨停价 即判定为涨停
BOARD_RULES = {
    "main": {"threshold": 9.97},       # 主板 10%
    "chi_next": {"threshold": 19.97},  # 创业板 20%
    "star": {"threshold": 19.97},      # 科创板 20%
    "bse": {"threshold": 29.97},       # 北交所 30%
}

EPSILON = 0.005  # 浮点比较容差


def classify_board(stock_code: str) -> str:
    """根据股票代码前缀判断所属板块"""
    if stock_code.startswith("60"):
        return "main"
    elif stock_code.startswith("00") or stock_code.startswith("30"):
        # 00xxxx 主板, 30xxxx 创业板
        if stock_code.startswith("30"):
            return "chi_next"
        return "main"
    elif stock_code.startswith("68"):
        return "star"
    elif stock_code.startswith("83") or stock_code.startswith("43"):
        return "bse"
    else:
        return "main"


def round2(value: float) -> float:
    """保留2位小数，四舍五入"""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def is_limit_up(close: float, prev_close: float, board: str) -> bool:
    """判断是否涨停

    Args:
        close: 收盘价
        prev_close: 前收盘价
        board: 板块

    Returns:
        True 如果涨停
    """
    if prev_close <= 0:
        return False

    threshold = BOARD_RULES[board]["threshold"]
    limit_price = round2(prev_close * (1 + threshold / 100))
    return close >= limit_price - EPSILON


def is_limit_down(close: float, prev_close: float, board: str) -> bool:
    """判断是否跌停（与涨停对称，方向相反）"""
    if prev_close <= 0:
        return False

    threshold = BOARD_RULES[board]["threshold"]
    limit_down_price = round2(prev_close * (1 - threshold / 100))
    return close <= limit_down_price + EPSILON


def count_board_break(db: Session, trade_date: date) -> dict:
    """统计破板数据

    破板 = 盘中触及涨停价(high >= limit_up_price) 但收盘未封板(close < limit_up_price - EPSILON)。
    返回 {"board_break_count": int, "board_break_rate": float}
    """
    rows = db.query(StockDailyRaw).filter(
        StockDailyRaw.trade_date == trade_date
    ).all()

    if not rows:
        return {"board_break_count": 0, "board_break_rate": 0.0}

    hit_limit_count = 0  # 触及涨停的股票数
    board_break_count = 0  # 未封板的股票数

    for row in rows:
        if row.close is None or row.high is None or row.pct_change is None:
            continue
        if row.pct_change <= -100:
            continue

        board = classify_board(row.stock_code)
        prev_close = round2(row.close / (1 + row.pct_change / 100))
        threshold = BOARD_RULES[board]["threshold"]
        limit_price = round2(prev_close * (1 + threshold / 100))

        # 盘中最高价触及涨停价
        if row.high >= limit_price - EPSILON:
            hit_limit_count += 1
            # 收盘未封住
            if row.close < limit_price - EPSILON:
                board_break_count += 1

    rate = round(board_break_count / hit_limit_count * 100, 1) if hit_limit_count > 0 else 0.0

    logger.info(
        f"{trade_date} 破板统计: 触及涨停 {hit_limit_count} 只, "
        f"破板 {board_break_count} 只, 破板率 {rate}%"
    )
    return {"board_break_count": board_break_count, "board_break_rate": rate}


def compute_limit_up(db: Session, trade_date: date) -> int:
    """从原始数据识别涨停股票，计算连板天数，存入 stock_limit_up 表

    Args:
        db: 数据库会话
        trade_date: 交易日期

    Returns:
        涨停股票数量
    """
    # 查询当日所有股票
    rows = db.query(StockDailyRaw).filter(
        StockDailyRaw.trade_date == trade_date
    ).all()

    if not rows:
        logger.warning(f"{trade_date} 无股票数据，无法统计涨停")
        return 0

    # 获取前一个交易日（用于连板计算）
    prev_date = (
        db.query(StockLimitUp.trade_date)
        .filter(StockLimitUp.trade_date < trade_date)
        .order_by(desc(StockLimitUp.trade_date))
        .limit(1)
        .scalar()
    )

    # 查前日涨停股票（用于连板累加）
    prev_limit_up: dict[str, int] = {}
    if prev_date:
        prev_rows = (
            db.query(StockLimitUp)
            .filter(StockLimitUp.trade_date == prev_date)
            .all()
        )
        prev_limit_up = {r.stock_code: r.consecutive for r in prev_rows}

    # 识别涨停股
    limit_up_stocks = []
    for row in rows:
        if row.close is None or row.pct_change is None:
            continue

        board = classify_board(row.stock_code)
        # 前收盘价 = close / (1 + pct_change/100)，反推昨收
        if row.pct_change is None or row.pct_change <= -100:
            continue
        prev_close = round2(row.close / (1 + row.pct_change / 100))

        if is_limit_up(row.close, prev_close, board):
            limit_up_price = round2(prev_close * (1 + BOARD_RULES[board]["threshold"] / 100))
            consecutive = prev_limit_up.get(row.stock_code, 0) + 1

            limit_up_stocks.append(
                StockLimitUp(
                    trade_date=trade_date,
                    stock_code=row.stock_code,
                    stock_name=row.stock_name,
                    limit_up_price=limit_up_price,
                    board=board,
                    pct_change=row.pct_change,
                    consecutive=consecutive,
                )
            )

    if not limit_up_stocks:
        logger.info(f"{trade_date} 无涨停股票")
        return 0

    # 清除当日旧数据（幂等）
    db.execute(
        delete(StockLimitUp).where(StockLimitUp.trade_date == trade_date)
    )

    db.add_all(limit_up_stocks)
    db.commit()

    max_consecutive = max(s.consecutive for s in limit_up_stocks)
    logger.info(f"{trade_date} 涨停股票已识别，共 {len(limit_up_stocks)} 只，最高连板 {max_consecutive}")
    return len(limit_up_stocks)
