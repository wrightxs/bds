"""数据源工厂，根据配置选择合适的 fetcher"""

from app.config import get_data_source
from app.fetcher.base import BaseFetcher


def get_fetcher() -> BaseFetcher:
    """根据当前数据源配置返回对应数据源实例"""
    source = get_data_source()
    if source == "tushare":
        from app.fetcher.tushare import TushareFetcher

        return TushareFetcher()
    else:
        from app.fetcher.akshare import AKShareFetcher

        return AKShareFetcher()
