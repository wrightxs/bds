"""数据库连接配置"""

import os

# 数据库连接 URL，从环境变量读取配置
DATABASE_URL = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER', 'stock_user')}:"
    f"{os.getenv('MYSQL_PASSWORD', 'stock_pass')}@"
    f"{os.getenv('MYSQL_HOST', 'localhost')}:"
    f"{os.getenv('MYSQL_PORT', '3306')}/"
    f"{os.getenv('MYSQL_DATABASE', 'stock_analysis')}"
    f"?charset=utf8mb4"
)

# 数据源类型：akshare 或 tushare（运行时可通过 set_data_source 切换）
_data_source = os.getenv("DATA_SOURCE", "tushare")


def get_data_source() -> str:
    return _data_source


def set_data_source(source: str) -> None:
    global _data_source
    if source not in ("akshare", "tushare"):
        raise ValueError(f"不支持的数据源: {source}，可选 akshare / tushare")
    _data_source = source


# Tushare token
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 定时任务触发时间（默认每天18:00）
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "18"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))
