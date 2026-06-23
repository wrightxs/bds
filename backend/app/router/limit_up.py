"""涨停股票 & 仪表盘 & 数据抓取 API"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import delete, func, desc

from app.database import get_db
from app.models import StockDailyRaw, StockLimitUp, StockTop100, StockInfo
from app.service.top100 import compute_top100
from app.service.limit_up import compute_limit_up, is_limit_down, count_board_break, classify_board, round2, BOARD_RULES

logger = logging.getLogger(__name__)

router = APIRouter(tags=["涨停股票"])

# 板块中文映射
BOARD_LABELS = {
    "main": "主板",
    "chi_next": "创业板",
    "star": "科创板",
    "bse": "北交所",
}


@router.get("/limit_up")
def get_limit_up(
    dt: date | None = Query(None, alias="date", description="交易日期，默认返回最新"),
    board: str | None = Query(None, description="板块筛选: main/chi_next/star/bse"),
    db: Session = Depends(get_db),
):
    """查询涨停股票列表，支持按板块筛选"""
    if dt is None:
        row = (
            db.query(StockLimitUp.trade_date)
            .order_by(StockLimitUp.trade_date.desc())
            .first()
        )
        if row is None:
            return {"date": None, "data": []}
        dt = row.trade_date

    q = db.query(StockLimitUp).filter(StockLimitUp.trade_date == dt)
    if board:
        q = q.filter(StockLimitUp.board == board)
    q = q.order_by(StockLimitUp.consecutive.desc(), StockLimitUp.pct_change.desc())

    rows = q.all()

    return {
        "date": dt.isoformat(),
        "data": [
            {
                "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "limit_up_price": float(r.limit_up_price) if r.limit_up_price else None,
                "board": r.board,
                "board_label": BOARD_LABELS.get(r.board, r.board),
                "pct_change": float(r.pct_change) if r.pct_change else None,
                "consecutive": r.consecutive,
            }
            for r in rows
        ],
    }


@router.get("/dashboard")
def get_dashboard(
    dt: date | None = Query(None, alias="date", description="交易日期，默认返回最新"),
    db: Session = Depends(get_db),
):
    """仪表盘摘要数据（含前2个工作日对比）"""
    if dt is None:
        row = (
            db.query(StockDailyRaw.trade_date)
            .order_by(StockDailyRaw.trade_date.desc())
            .first()
        )
        if row is None:
            return {"date": None, "total_turnover": 0, "limit_up_count": 0, "top_stock": None, "comparison": []}
        dt = row.trade_date

    # 前2个交易日日期
    prev_dates = (
        db.query(StockDailyRaw.trade_date)
        .filter(StockDailyRaw.trade_date < dt)
        .distinct()
        .order_by(StockDailyRaw.trade_date.desc())
        .limit(2)
        .all()
    )
    prev_dates = [r.trade_date for r in prev_dates]

    def day_summary(d: date) -> dict:
        """计算单个交易日的数据摘要"""
        total_amount = (
            db.query(func.sum(StockDailyRaw.amount))
            .filter(StockDailyRaw.trade_date == d)
            .scalar()
        ) or 0
        limit_up_count = (
            db.query(func.count(StockLimitUp.id))
            .filter(StockLimitUp.trade_date == d)
            .scalar()
        ) or 0
        stock_count = (
            db.query(func.count(StockDailyRaw.id))
            .filter(StockDailyRaw.trade_date == d)
            .scalar()
        ) or 0

        # 跌停数量
        limit_down_count = 0
        raw_rows = db.query(StockDailyRaw).filter(StockDailyRaw.trade_date == d).all()
        for r in raw_rows:
            if r.close is None or r.pct_change is None or r.pct_change <= -100:
                continue
            board = classify_board(r.stock_code)
            prev_close = round2(r.close / (1 + r.pct_change / 100))
            if is_limit_down(r.close, prev_close, board):
                limit_down_count += 1

        # 破板统计
        bb = count_board_break(db, d)

        return {
            "date": d.isoformat(),
            "total_turnover": float(total_amount),
            "stock_count": stock_count,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "board_break_count": bb["board_break_count"],
            "board_break_rate": bb["board_break_rate"],
        }

    # 当日摘要
    current = day_summary(dt)

    # 前2个交易日摘要
    comparison = [day_summary(d) for d in prev_dates]

    return {
        "date": current["date"],
        "total_turnover": current["total_turnover"],
        "stock_count": current["stock_count"],
        "limit_up_count": current["limit_up_count"],
        "limit_down_count": current["limit_down_count"],
        "board_break_count": current["board_break_count"],
        "board_break_rate": current["board_break_rate"],
        "comparison": comparison,
    }


@router.post("/fetch")
def trigger_fetch(
    dt: date | None = Query(None, alias="date", description="抓取日期，默认今天"),
    force: bool = Query(False, description="强制重新抓取，覆盖已有数据"),
    db: Session = Depends(get_db),
):
    """手动触发数据抓取（也可用于定时任务调用）

    - 当日数据使用实时行情接口（约 30 秒）
    - 历史数据逐只查询（约 10 分钟）
    - 默认跳过已有数据的日期，传 force=true 强制覆盖
    """
    from app.fetcher import get_fetcher
    from app.service.top100 import compute_top100
    from app.service.limit_up import compute_limit_up

    if dt is None:
        dt = date.today()

    # 幂等检查：数据已存在则跳过
    existing = (
        db.query(func.count(StockDailyRaw.id))
        .filter(StockDailyRaw.trade_date == dt)
        .scalar()
    ) or 0

    if existing > 0 and not force:
        logger.info(f"{dt} 数据已存在（{existing} 条），跳过抓取")
        return {
            "date": dt.isoformat(),
            "raw_count": existing,
            "top100_count": (
                db.query(func.count(StockTop100.id))
                .filter(StockTop100.trade_date == dt)
                .scalar() or 0
            ),
            "limit_up_count": (
                db.query(func.count(StockLimitUp.id))
                .filter(StockLimitUp.trade_date == dt)
                .scalar() or 0
            ),
            "skipped": True,
        }

    fetcher = get_fetcher()

    # 从数据库获取已有股票名称（Tushare 免费版 stock_basic 限频 1次/小时）
    stock_names = {}
    try:
        name_rows = (
            db.query(StockDailyRaw.stock_code, StockDailyRaw.stock_name)
            .distinct(StockDailyRaw.stock_code)
            .all()
        )
        stock_names = {r.stock_code: r.stock_name for r in name_rows}
    except Exception:
        pass

    # 1. 从数据源获取原始数据
    try:
        raw_data = fetcher.fetch_daily_data(dt, stock_names)
    except Exception as e:
        logger.exception(f"数据源获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据源获取失败: {e}")

    if not raw_data:
        raise HTTPException(status_code=404, detail=f"{dt} 无交易数据（可能是非交易日）")

    # 2. 批量写入原始数据（先删后插）
    if existing > 0:
        db.execute(delete(StockDailyRaw).where(StockDailyRaw.trade_date == dt))
        db.commit()

    records = [
        StockDailyRaw(
            trade_date=r.get("trade_date", dt),
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
    logger.info(f"{dt} 原始数据已写入，共 {len(records)} 条")

    # 3. 生成 top100
    top100_count = compute_top100(db, dt)

    # 4. 识别涨停
    limit_up_count = compute_limit_up(db, dt)

    # 5. 同步行业分类（首次运行或定期刷新）
    industry_count = 0
    try:
        existing_info = db.query(func.count(StockInfo.stock_code)).scalar() or 0
        if existing_info < 1000:  # 行业数据不足时补充
            code_industry = fetcher.fetch_stock_industry()
            if code_industry:
                from sqlalchemy.dialects.mysql import insert
                for code, ind in code_industry.items():
                    stmt = (
                        insert(StockInfo)
                        .values(stock_code=code, industry=ind)
                        .on_duplicate_key_update(industry=ind)
                    )
                    db.execute(stmt)
                db.commit()
                industry_count = len(code_industry)
                logger.info(f"行业分类同步完成，共 {industry_count} 条")
    except Exception as e:
        logger.warning(f"同步行业分类失败（不影响主流程）: {e}")

    return {
        "date": dt.isoformat(),
        "raw_count": len(records),
        "top100_count": top100_count,
        "limit_up_count": limit_up_count,
        "industry_count": industry_count,
        "is_historical": dt < date.today(),
    }


@router.get("/dates")
def get_dates(db: Session = Depends(get_db)):
    """查询数据库中已有的交易日期列表"""
    rows = (
        db.query(StockDailyRaw.trade_date)
        .distinct()
        .order_by(desc(StockDailyRaw.trade_date))
        .limit(60)
        .all()
    )
    return {"dates": [r.trade_date.isoformat() for r in rows]}


@router.get("/data-source")
def get_data_source_config():
    """获取当前数据源配置"""
    from app.config import get_data_source

    return {"data_source": get_data_source()}


@router.post("/data-source")
def set_data_source_config(source: str = Query(..., description="数据源: akshare 或 tushare")):
    """切换数据源（运行时生效）"""
    from app.config import set_data_source

    try:
        set_data_source(source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info(f"数据源已切换为: {source}")
    return {"data_source": source, "message": f"数据源已切换为 {source}"}
