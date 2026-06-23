"""Tushare 数据源实现

通过 Tushare Pro API 获取全市场日线数据，一次调用即可覆盖所有股票。
"""

import logging
from datetime import date
from typing import Any

import tushare as ts

from app.config import TUSHARE_TOKEN
from app.fetcher.base import BaseFetcher

logger = logging.getLogger(__name__)


class TushareFetcher(BaseFetcher):
    """通过 Tushare Pro API 获取全市场股票行情数据"""

    def __init__(self):
        if not TUSHARE_TOKEN:
            raise ValueError("Tushare token 未配置，请在 .env 中设置 TUSHARE_TOKEN")
        ts.set_token(TUSHARE_TOKEN)
        self._pro = ts.pro_api()
        self._stock_names: dict[str, str] | None = None  # 延迟加载

    def _get_stock_names(self) -> dict[str, str]:
        """获取全量股票代码→名称映射（缓存）"""
        if self._stock_names is not None:
            return self._stock_names

        logger.info("从 Tushare 获取股票列表...")
        try:
            df = self._pro.stock_basic(
                exchange="", list_status="L",
                fields="ts_code,name",
            )
        except Exception as e:
            raise RuntimeError(f"获取股票列表失败: {e}") from e

        self._stock_names = {}
        for _, row in df.iterrows():
            code = row["ts_code"].split(".")[0]  # 去掉 .SZ/.SH 后缀
            self._stock_names[code] = row["name"]

        logger.info(f"获取到 {len(self._stock_names)} 只股票名称")
        return self._stock_names

    def fetch_daily_data(self, trade_date: date) -> list[dict[str, Any]]:
        """获取指定交易日全市场股票数据

        Tushare daily 接口一次返回全市场数据，速度快。
        """
        date_str = trade_date.strftime("%Y%m%d")
        logger.info(f"Tushare 获取 {trade_date} 全市场日线数据...")

        try:
            df = self._pro.daily(trade_date=date_str)
        except Exception as e:
            raise RuntimeError(f"Tushare daily 接口调用失败: {e}") from e

        if df is None or df.empty:
            logger.warning(f"{trade_date} 无交易数据")
            return []

        # 按成交额降序
        df = df.sort_values("amount", ascending=False)

        # 获取股票名称
        names = self._get_stock_names()

        results = []
        for _, row in df.iterrows():
            code = row["ts_code"].split(".")[0]
            close_val = float(row["close"])
            pre_close_val = float(row["pre_close"])

            if close_val <= 0:
                continue

            # 成交量：手 → 股
            vol = float(row["vol"]) * 100 if row.get("vol") is not None else None

            # 成交额：千元 → 元
            amount = float(row["amount"]) * 1000 if row.get("amount") is not None else None

            # 涨跌幅（Tushare 已有）
            pct_change = float(row["pct_chg"]) if row.get("pct_chg") is not None else None

            results.append({
                "trade_date": trade_date,
                "stock_code": code,
                "stock_name": names.get(code, ""),
                "open": float(row["open"]) if row.get("open") is not None else None,
                "close": close_val,
                "high": float(row["high"]) if row.get("high") is not None else None,
                "low": float(row["low"]) if row.get("low") is not None else None,
                "volume": int(vol) if vol else None,
                "amount": amount,
                "pct_change": pct_change,
                "turnover_rate": None,
                "prev_close": pre_close_val if pre_close_val > 0 else None,
            })

        logger.info(f"Tushare 获取完成，有效数据 {len(results)} 条")
        return results
