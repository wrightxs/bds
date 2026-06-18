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

# 数据源类型：akshare 或 tushare
DATA_SOURCE = os.getenv("DATA_SOURCE", "akshare")
# Tushare token（后期对接时使用）
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 定时任务触发时间（默认每天18:00）
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "18"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))
