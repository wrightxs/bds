"""AKShare 数据源实现

使用东方财富实时行情接口获取全市场股票数据。
每天18:00后调用可获取当日收盘数据。
"""

from datetime import date
from typing import Any

import akshare as ak
import pandas as pd

from app.fetcher.base import BaseFetcher

# AKShare spot 接口返回的列名映射
COLUMN_MAP = {
    "代码": "stock_code",
    "名称": "stock_name",
    "今开": "open",
    "最新价": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "涨跌幅": "pct_change",
    "换手率": "turnover_rate",
    "昨收": "prev_close",
}


class AKShareFetcher(BaseFetcher):
    """通过 AKShare 获取东方财富实时行情数据"""

    def fetch_daily_data(self, trade_date: date) -> list[dict[str, Any]]:
        """获取全市场股票日线数据

        调用 ak.stock_zh_a_spot_em() 获取实时行情，
        返回统一格式的股票数据列表。
        """
        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            raise RuntimeError(f"AKShare 数据获取失败: {e}") from e

        if df is None or df.empty:
            return []

        # 重命名列
        df = df.rename(columns=COLUMN_MAP)

        # 只保留需要的列
        needed_cols = list(COLUMN_MAP.values())
        available_cols = [c for c in needed_cols if c in df.columns]
        df = df[available_cols]

        # 数值类型转换
        numeric_cols = ["open", "close", "high", "low", "amount", "pct_change", "turnover_rate", "prev_close"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")

        # 过滤掉无效数据（无成交额的股票）
        if "amount" in df.columns:
            df = df[df["amount"] > 0]

        # 添加交易日期
        df["trade_date"] = trade_date

        # 替换 NaN 为 None，便于数据库存储
        df = df.where(pd.notnull(df), None)

        return df.to_dict("records")
