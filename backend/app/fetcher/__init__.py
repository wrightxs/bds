"""数据源工厂，根据配置选择合适的 fetcher"""

from app.config import DATA_SOURCE
from app.fetcher.base import BaseFetcher


def get_fetcher() -> BaseFetcher:
    """根据环境变量 DATA_SOURCE 返回对应数据源实例"""
    if DATA_SOURCE == "tushare":
        from app.fetcher.tushare import TushareFetcher

        return TushareFetcher()
    else:
        from app.fetcher.akshare import AKShareFetcher

        return AKShareFetcher()
