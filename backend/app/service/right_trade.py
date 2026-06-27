"""右侧交易分析 — 均线突破策略

基于成熟均线策略筛选底部反转股票：
- 10天：底部区域 + 首次突破10日均线（昨日≤MA10 < 今日收盘）
- 20天：底部区域 + 收盘站稳10日均线上方
- 30天：底部区域 + 金叉（收盘同时站上10、20、30日均线）
"""

import logging
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import StockDailyRaw

logger = logging.getLogger(__name__)

LOOKBACK = 30  # 均线计算需要的回看交易日数（数据充足后改为60）
BOTTOM_RANGE = 1.20  # 当前价在周期最低价的 120% 内视为底部区域
MIN_DATA_DAYS = 5  # 最少需要的交易日数


def get_recent_trading_dates(db: Session, end_date, days: int) -> list:
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


def compute_ma(prices: list[float], period: int) -> float | None:
    """计算 period 日均线值，数据不足时用已有数据近似"""
    if len(prices) < 2:
        return None
    n = min(period, len(prices))
    return round(sum(prices[:n]) / n, 2)


def is_bottom_area(close: float, period_low: float) -> bool:
    """判断当前价是否在底部区域（距离周期最低点 20% 以内）"""
    if period_low <= 0:
        return False
    return close <= period_low * BOTTOM_RANGE


def compute_right_trade(
    db: Session, trade_date, days: int
) -> list[dict]:
    """均线突破筛选

    Args:
        days: 筛选周期（10/20/30），用于前端展示标签
    """
    # 取足够长数据计算均线
    dates = get_recent_trading_dates(db, trade_date, LOOKBACK)
    if len(dates) < MIN_DATA_DAYS:
        logger.warning(f"数据不足: 仅有 {len(dates)} 个交易日，需要至少 {MIN_DATA_DAYS}")
        return []

    date_set = set(dates)
    latest_date = dates[0]  # 最新
    prev_date = dates[1] if len(dates) > 1 else None  # 前一日

    # 查询全量数据
    rows = (
        db.query(StockDailyRaw)
        .filter(StockDailyRaw.trade_date.in_(date_set))
        .all()
    )

    if not rows:
        return []

    # 按股票分组，收集收盘价序列（日期升序: 旧→新）
    stock_data: dict[str, dict] = defaultdict(lambda: {"name": "", "dates": [], "closes": []})

    for r in rows:
        if r.close and r.close > 0:
            stock_data[r.stock_code]["name"] = r.stock_name
            stock_data[r.stock_code]["dates"].append(r.trade_date)
            stock_data[r.stock_code]["closes"].append(float(r.close))

    results = []

    for code, sd in stock_data.items():
        if len(sd["closes"]) < MIN_DATA_DAYS:
            continue

        # 按日期升序排列
        pairs = sorted(zip(sd["dates"], sd["closes"]), key=lambda x: x[0])
        sorted_dates = [p[0] for p in pairs]
        sorted_closes = [p[1] for p in pairs]

        # 当前收盘价（latest_date 可能不在该股票的数据中）
        if latest_date not in sd["dates"]:
            continue
        idx_latest = sorted_dates.index(latest_date)
        current_close = sorted_closes[idx_latest]

        # 周期最低价
        period_low = min(sorted_closes)

        # 底部区域判断
        if not is_bottom_area(current_close, period_low):
            continue

        # 计算均线（取最近 N 天的均值，从最新日期往前数）
        closes_desc = list(reversed(sorted_closes))  # 新→旧
        ma10 = compute_ma(closes_desc, 10)
        ma20 = compute_ma(closes_desc, 20)
        ma30 = compute_ma(closes_desc, 30)

        if ma10 is None or ma20 is None or ma30 is None:
            continue

        bottom_pct = round((current_close / period_low - 1) * 100, 2)

        # 根据周期应用规则
        signal = None

        if days == 10:
            # 首次突破10日线：昨日 ≤ MA10，今日 > MA10
            if prev_date and prev_date in sd["dates"]:
                idx_prev = sorted_dates.index(prev_date)
                prev_close = sorted_closes[idx_prev]
                if prev_close <= ma10 and current_close > ma10:
                    signal = "首次突破10日线"
            # 如果没有前一日数据，退化为今日站上即可
            elif current_close > ma10:
                # 往前找最近一个 ≤ MA10 的日子确认是首次突破
                crossed = False
                for i in range(idx_latest - 1, -1, -1):
                    if sorted_closes[i] <= ma10:
                        crossed = True
                        break
                    elif sorted_closes[i] > ma10:
                        continue
                if crossed:
                    signal = "首次突破10日线"

        elif days == 20:
            # 站上10日线
            if current_close > ma10:
                signal = "站上10日线"

        elif days == 30:
            # 金叉：同时站上 10/20/30 日线
            if current_close > ma10 and current_close > ma20 and current_close > ma30:
                signal = "金叉"

        if signal is None:
            continue

        results.append({
            "stock_code": code,
            "stock_name": sd["name"],
            "close": round(current_close, 2),
            "ma10": ma10,
            "ma20": ma20,
            "ma30": ma30,
            "bottom_low": round(period_low, 2),
            "bottom_pct": bottom_pct,
            "signal": signal,
        })

    # 按信号分组排序：金叉优先，然后站上10日线，最后首次突破
    signal_order = {"金叉": 0, "站上10日线": 1, "首次突破10日线": 2}
    results.sort(key=lambda x: (signal_order.get(x["signal"], 99), -x["bottom_pct"]))

    logger.info(
        f"均线突破筛选完成: {trade_date}, 周期{days}天, "
        f"有效股票 {len(stock_data)} 只, 筛选出 {len(results)} 只"
    )
    return results
