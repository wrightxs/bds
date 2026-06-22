from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockDailyRaw(Base):
    """股票每日原始数据"""

    __tablename__ = "stock_daily_raw"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="股票代码")
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")
    open: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True, comment="开盘价")
    close: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True, comment="收盘价")
    high: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True, comment="最高价")
    low: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True, comment="最低价")
    volume: Mapped[int] = mapped_column(BigInteger, nullable=True, comment="成交量（股）")
    amount: Mapped[float] = mapped_column(Numeric(16, 2), nullable=True, comment="成交额（元）")
    pct_change: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True, comment="涨跌幅（%）")
    turnover_rate: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True, comment="换手率（%）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_date_amount", "trade_date", "amount"),
        Index("idx_date_pct", "trade_date", "pct_change"),
        UniqueConstraint("trade_date", "stock_code", name="uk_date_code"),
    )


class StockTop100(Base):
    """每日成交额前100股票"""

    __tablename__ = "stock_top100"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    rank: Mapped[int] = mapped_column(Integer, nullable=False, comment="排名（1-100）")
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="股票代码")
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")
    amount: Mapped[float] = mapped_column(Numeric(16, 2), nullable=True, comment="成交额（元）")
    pct_change: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True, comment="涨跌幅（%）")
    close: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True, comment="收盘价")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_date_rank", "trade_date", "rank"),
        UniqueConstraint("trade_date", "rank", name="uk_date_rank"),
    )


class StockLimitUp(Base):
    """每日涨停股票"""

    __tablename__ = "stock_limit_up"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="股票代码")
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")
    limit_up_price: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True, comment="涨停价")
    board: Mapped[str] = mapped_column(String(20), nullable=False, comment="板块（主板/创业板/科创板/北交所）")
    pct_change: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True, comment="涨跌幅（%）")
    consecutive: Mapped[int] = mapped_column(Integer, default=1, comment="连板天数")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        UniqueConstraint("trade_date", "stock_code", name="uk_date_code"),
        Index("idx_date_board", "trade_date", "board"),
    )


class StockInfo(Base):
    """股票基本信息（行业分类等元数据）"""

    __tablename__ = "stock_info"

    stock_code: Mapped[str] = mapped_column(String(10), primary_key=True, comment="股票代码")
    stock_name: Mapped[str] = mapped_column(String(50), nullable=True, comment="股票名称")
    industry: Mapped[str] = mapped_column(String(100), nullable=True, comment="申万一级行业")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
