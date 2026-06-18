"""数据源抽象基类"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class BaseFetcher(ABC):
    """数据源抽象基类，所有数据源需实现此接口"""

    @abstractmethod
    def fetch_daily_data(self, trade_date: date) -> list[dict[str, Any]]:
        """获取指定交易日全市场股票数据

        Args:
            trade_date: 交易日期

        Returns:
            股票数据列表，每项包含：
            - stock_code: 股票代码
            - stock_name: 股票名称
            - open: 开盘价
            - close: 收盘价
            - high: 最高价
            - low: 最低价
            - volume: 成交量
            - amount: 成交额
            - pct_change: 涨跌幅
            - turnover_rate: 换手率
            - prev_close: 前收盘价（用于涨停判断）
        """
        ...
