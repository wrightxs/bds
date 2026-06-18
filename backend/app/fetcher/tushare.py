"""Tushare 数据源（后期对接用）"""

from datetime import date
from typing import Any

from app.config import TUSHARE_TOKEN
from app.fetcher.base import BaseFetcher


class TushareFetcher(BaseFetcher):
    """通过 Tushare Pro 获取股票数据

    TODO: 后期对接 Tushare 时实现此数据源。
    需要配置 TUSHARE_TOKEN 环境变量。
    """

    def __init__(self):
        if not TUSHARE_TOKEN:
            raise ValueError("Tushare token 未配置，请设置 TUSHARE_TOKEN 环境变量")
        # TODO: import tushare as ts
        # ts.set_token(TUSHARE_TOKEN)
        # self.pro = ts.pro_api()

    def fetch_daily_data(self, trade_date: date) -> list[dict[str, Any]]:
        """获取全市场股票日线数据（待实现）"""
        raise NotImplementedError("Tushare 数据源尚未实现")
