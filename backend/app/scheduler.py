"""定时任务调度器

每个交易日18:00自动执行数据抓取和统计分析。
"""

import logging
from datetime import date, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import SCHEDULE_HOUR, SCHEDULE_MINUTE

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def fetch_daily_job():
    """每日定时任务：抓取数据并统计"""
    from app.database import SessionLocal
    from app.models import StockDailyRaw

    today = date.today()
    logger.info(f"定时任务触发：{today}")

    db = SessionLocal()
    try:
        # 检查今日数据是否已存在（幂等保护）
        from sqlalchemy import func

        exists = (
            db.query(func.count(StockDailyRaw.id))
            .filter(StockDailyRaw.trade_date == today)
            .scalar()
        ) > 0

        if exists:
            logger.info(f"{today} 数据已存在，跳过")
            return

        from app.fetcher import get_fetcher
        from app.service.top100 import compute_top100
        from app.service.limit_up import compute_limit_up
        from sqlalchemy import delete
        import sqlalchemy

        fetcher = get_fetcher()

        # 1. 抓取原始数据
        raw_data = fetcher.fetch_daily_data(today)
        if not raw_data:
            logger.info(f"{today} 无交易数据（非交易日或休市）")
            return

        # 2. 写入原始数据
        records = [
            StockDailyRaw(
                trade_date=r.get("trade_date", today),
                stock_code=r["stock_code"],
                stock_name=r["stock_name"],
                open=r.get("open"),
                close=r.get("close"),
                high=r.get("high"),
                low=r.get("low"),
                volume=r.get("volume"),
                amount=r.get("amount"),
                pct_change=r.get("pct_change"),
                turnover_rate=r.get("turnover_rate"),
            )
            for r in raw_data
        ]
        db.add_all(records)
        db.commit()
        logger.info(f"{today} 原始数据写入完成，共 {len(records)} 条")

        # 3. 统计 top100
        compute_top100(db, today)

        # 4. 识别涨停
        compute_limit_up(db, today)

        logger.info(f"{today} 数据统计全部完成")
    except Exception:
        logger.exception(f"{today} 定时任务执行失败")
    finally:
        db.close()


def start_scheduler():
    """启动定时任务"""
    scheduler.add_job(
        fetch_daily_job,
        trigger=CronTrigger(
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            day_of_week="mon-fri",
        ),
        id="fetch_daily",
        name="每日股票数据抓取",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"定时任务已启动，触发时间：工作日 {SCHEDULE_HOUR}:{SCHEDULE_MINUTE:02d}")
