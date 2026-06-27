"""缠论买卖点检测

简化实现：
- 1买：周期最低点已出现，价格从低点反弹 ≥3%，低点处成交量收缩
- 2买：前期低点反弹后回踩，回踩低点 > 前期低点，且再次企稳
"""

import logging
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import StockDailyRaw

logger = logging.getLogger(__name__)

LOOKBACK = 30
MIN_AMOUNT = 1e8  # 成交额 > 1亿
MIN_REBOUND = 1.03  # 反弹 ≥3%


def get_recent_trading_dates(db: Session, end_date, days: int) -> list:
    rows = (
        db.query(StockDailyRaw.trade_date)
        .filter(StockDailyRaw.trade_date <= end_date)
        .distinct()
        .order_by(desc(StockDailyRaw.trade_date))
        .limit(days)
        .all()
    )
    return [r.trade_date for r in rows]


def compute_chan_theory(db: Session, trade_date) -> dict:
    dates = get_recent_trading_dates(db, trade_date, LOOKBACK)
    if len(dates) < 5:
        return {"buy1": [], "buy2": []}

    date_set = set(dates)
    latest_date = dates[0]

    rows = (
        db.query(StockDailyRaw)
        .filter(StockDailyRaw.trade_date.in_(date_set))
        .all()
    )
    if not rows:
        return {"buy1": [], "buy2": []}

    stock_data = defaultdict(lambda: {"name": "", "dates": [], "closes": [], "volumes": [], "amounts": []})
    for r in rows:
        if r.close and r.close > 0:
            sd = stock_data[r.stock_code]
            sd["name"] = r.stock_name
            sd["dates"].append(r.trade_date)
            sd["closes"].append(float(r.close))
            sd["volumes"].append(float(r.volume) if r.volume else 0)
            sd["amounts"].append(float(r.amount) if r.amount else 0)

    buy1_list = []
    buy2_list = []

    for code, sd in stock_data.items():
        if len(sd["closes"]) < 5:
            continue

        pairs = sorted(zip(sd["dates"], sd["closes"], sd["volumes"], sd["amounts"]), key=lambda x: x[0])
        sorted_dates = [p[0] for p in pairs]
        closes = [p[1] for p in pairs]
        volumes = [p[2] for p in pairs]
        amounts = [p[3] for p in pairs]

        if latest_date not in sd["dates"]:
            continue
        idx_latest = sorted_dates.index(latest_date)
        current_close = closes[idx_latest]
        current_amount = amounts[idx_latest]

        # 找周期最低点
        period_low = min(closes)
        low_idx = closes.index(period_low)

        # 最低点必须在至少 2 天前（不是今天才新低）
        if low_idx >= idx_latest - 1:
            continue

        rebound_pct = (current_close / period_low - 1) * 100

        # ── 1买：从最低点反弹 ≥3%，且低点成交量低于前一波 ──
        if rebound_pct >= 3:
            # 计算低点附近平均成交量 vs 前期平均成交量
            low_vol = sum(volumes[max(0, low_idx - 1):low_idx + 1])
            prev_vol = sum(volumes[max(0, low_idx - 5):low_idx - 1]) / max(1, min(4, low_idx - 1))
            if prev_vol > 0 and low_vol < prev_vol:
                if current_amount >= MIN_AMOUNT:
                    buy1_list.append({
                        "stock_code": code,
                        "stock_name": sd["name"],
                        "close": round(current_close, 2),
                        "low_price": round(period_low, 2),
                        "low_date": sorted_dates[low_idx].isoformat(),
                        "rebound_pct": round(rebound_pct, 2),
                        "amount": round(current_amount, 0),
                        "signal": "1买",
                    })

        # ── 2买：最低点已反弹过，近期有回踩（>前低），当前企稳 ──
        # 找近期局部低点（回踩点）：最近 3 天内的最低收盘价
        if low_idx < idx_latest - 2:
            recent_segment = closes[low_idx + 1:]  # 最低点之后的数据
            if len(recent_segment) >= 3:
                pullback_low = min(recent_segment[-3:])  # 近3天最低
                pullback_idx = low_idx + 1 + recent_segment.index(pullback_low)
                # 回踩点必须高于前低
                if pullback_low > period_low and pullback_idx < idx_latest:
                    # 当前从回踩点回升
                    if current_close > pullback_low * 1.01:
                        if current_amount >= MIN_AMOUNT:
                            buy2_list.append({
                                "stock_code": code,
                                "stock_name": sd["name"],
                                "close": round(current_close, 2),
                                "prev_low": round(period_low, 2),
                                "prev_low_date": sorted_dates[low_idx].isoformat(),
                                "pullback_low": round(pullback_low, 2),
                                "rebound_pct": round(rebound_pct, 2),
                                "amount": round(current_amount, 0),
                                "signal": "2买",
                            })

    buy1_list.sort(key=lambda x: x["rebound_pct"], reverse=True)
    buy2_list.sort(key=lambda x: x["rebound_pct"], reverse=True)
    logger.info(f"缠论检测: 1买={len(buy1_list)} 2买={len(buy2_list)}")
    return {"buy1": buy1_list, "buy2": buy2_list}
