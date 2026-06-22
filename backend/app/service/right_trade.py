"""右侧交易分析 — 筛选近N天从低点反弹>15%且未跌破起涨点的股票

三个周期使用同一日期区间（最近N天），但通过差异化约束筛选不同阶段的反弹：
- 10天：低点 ≥1天前，涨幅 ≥10%（捕捉近期快速反转）
- 20天：低点 ≥3天前，涨幅 ≥15%（捕捉中期确立反转）
- 30天：低点 ≥5天前，涨幅 ≥15%（捕捉远期确认反转）

短周期看快反弹，长周期看稳反弹，结果自然分化。
"""

import logging
from datetime import date
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import StockDailyRaw

logger = logging.getLogger(__name__)

# 周期参数：(最低反弹涨幅%, 低点距今最少交易天数)
PERIOD_PARAMS = {
    10: (10.0, 1),
    20: (15.0, 3),
    30: (15.0, 5),
}


def get_recent_trading_dates(db: Session, end_date: date, days: int) -> list[date]:
    """获取最近 N 个交易日的日期列表（降序: 最新在前）"""
    rows = (
        db.query(StockDailyRaw.trade_date)
        .filter(StockDailyRaw.trade_date <= end_date)
        .distinct()
        .order_by(desc(StockDailyRaw.trade_date))
        .limit(days)
        .all()
    )
    return [r.trade_date for r in rows]


def compute_right_trade(
    db: Session, trade_date: date, days: int
) -> list[dict]:
    """筛选右侧交易标的

    - 10天周期：低点距今 ≥1 天，涨幅 ≥10% → 近期快速反转
    - 20天周期：低点距今 ≥3 天，涨幅 ≥15% → 中期确立反转
    - 30天周期：低点距今 ≥5 天，涨幅 ≥15% → 远期确认反转
    """
    rise_threshold, min_low_age = PERIOD_PARAMS.get(days, (15.0, 1))

    dates = get_recent_trading_dates(db, trade_date, days)
    if len(dates) < 3:
        logger.warning(f"交易日不足 3 天（实际 {len(dates)} 天），无法分析")
        return []

    date_set = set(dates)
    latest_date = dates[0]  # 最新交易日

    # 查询周期内所有股票数据
    rows = (
        db.query(StockDailyRaw)
        .filter(StockDailyRaw.trade_date.in_(date_set))
        .all()
    )

    if not rows:
        return []

    # 按股票分组
    stock_prices: dict[str, dict[date, float]] = defaultdict(dict)
    stock_names: dict[str, str] = {}

    for r in rows:
        if r.close and r.close > 0:
            stock_prices[r.stock_code][r.trade_date] = float(r.close)
            stock_names[r.stock_code] = r.stock_name

    results = []

    for code, prices in stock_prices.items():
        if len(prices) < 3:
            continue

        sorted_dates = sorted(prices.keys())
        if len(sorted_dates) < 3:
            continue

        # 限制低点搜索范围：排除最近 min_low_age 个交易日
        # sorted_dates 升序（旧→新），最后 N 个是最新的
        low_search_end = len(sorted_dates) - min_low_age
        if low_search_end <= 0:
            continue  # 数据不够满足最低日数要求

        # 在允许范围内找最低收盘价
        low_date = None
        low_price = float("inf")
        for i in range(low_search_end):
            d = sorted_dates[i]
            if d in date_set and prices[d] < low_price:
                low_price = prices[d]
                low_date = d

        if low_date is None or low_price <= 0:
            continue

        # 低点之后的最高收盘价
        high_price = low_price
        for d in sorted_dates:
            if d >= low_date and prices[d] > high_price:
                high_price = prices[d]

        max_rise_pct = round((high_price / low_price - 1) * 100, 2)

        # 条件1: 最大涨幅 ≥ 阈值（不同周期阈值不同）
        if max_rise_pct < rise_threshold:
            continue

        # 最新收盘价
        current_close = prices.get(latest_date)
        if current_close is None:
            for d in reversed(sorted_dates):
                if d in date_set:
                    current_close = prices[d]
                    break

        if current_close is None:
            continue

        # 条件2: 当前价 > 低点
        if current_close <= low_price:
            continue

        from_low_pct = round((current_close / low_price - 1) * 100, 2)

        results.append({
            "stock_code": code,
            "stock_name": stock_names.get(code, ""),
            "low_date": low_date.isoformat(),
            "low_price": round(low_price, 2),
            "high_price": round(high_price, 2),
            "max_rise_pct": max_rise_pct,
            "current_close": round(current_close, 2),
            "from_low_pct": from_low_pct,
        })

    results.sort(key=lambda x: x["max_rise_pct"], reverse=True)

    logger.info(
        f"右侧交易分析完成: {trade_date}, {days}天周期"
        f"(阈值≥{rise_threshold}%, 低点≥{min_low_age}天前), "
        f"有效股票 {len(stock_prices)} 只, 筛选出 {len(results)} 只"
    )
    return results
