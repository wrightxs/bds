"""AKShare 数据源实现

使用新浪财经接口获取全市场股票日线数据。
East Money API 从部分 IP 可能无法访问，新浪作为主数据源，
AKShare 的 stock_info_a_code_name 用于获取股票列表。
"""

import logging
import re
import time
from datetime import date
from typing import Any

import akshare as ak
import pandas as pd
import requests

from app.fetcher.base import BaseFetcher

logger = logging.getLogger(__name__)

# 新浪行情接口，每次最多请求约 80 只股票（避免 URL 过长）
BATCH_SIZE = 80
# 请求间隔（秒），避免被反爬
REQUEST_INTERVAL = 0.3


class AKShareFetcher(BaseFetcher):
    """通过新浪财经接口获取全市场股票行情数据"""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://finance.sina.com.cn/",
        })

    def _sina_code(self, stock_code: str) -> str:
        """将纯数字代码转为新浪格式（sh600000 / sz000001）"""
        if stock_code.startswith(("60", "68")):
            return f"sh{stock_code}"
        else:
            return f"sz{stock_code}"

    def _parse_sina_line(self, line: str, trade_date: date) -> dict[str, Any] | None:
        """解析新浪单条行情数据

        格式示例:
        var hq_str_sh600000="浦发银行,9.20,9.24,9.09,9.20,..."
        """
        match = re.search(r'hq_str_(\w+)="(.+)"', line)
        if not match:
            return None

        sina_code = match.group(1)
        fields = match.group(2).split(",")
        if len(fields) < 32:
            return None

        # 提取纯数字代码
        stock_code = sina_code[2:]

        try:
            name = fields[0]           # 股票名称
            open_price = fields[1]     # 今开盘
            prev_close = fields[2]     # 昨收盘
            current = fields[3]        # 当前价
            high = fields[4]           # 最高价
            low = fields[5]            # 最低价
            volume = fields[8]         # 成交量（股）
            amount = fields[9]         # 成交额（元）

            open_val = float(open_price) if open_price else None
            close_val = float(current) if current else None
            high_val = float(high) if high else None
            low_val = float(low) if low else None
            prev_close_val = float(prev_close) if prev_close else None
            volume_val = int(float(volume)) if volume else None
            amount_val = float(amount) if amount else None

            # 计算涨跌幅
            if close_val and prev_close_val and prev_close_val > 0:
                pct_change = round((close_val / prev_close_val - 1) * 100, 2)
            else:
                pct_change = None

            # 换手率需要从字段 38 左右获取，新浪不同股票字段数可能不同
            turnover_rate = None

            # 过滤无效数据
            if close_val is None or close_val <= 0:
                return None
            if volume_val is None or volume_val <= 0:
                return None

            return {
                "trade_date": trade_date,
                "stock_code": stock_code,
                "stock_name": name,
                "open": open_val,
                "close": close_val,
                "high": high_val,
                "low": low_val,
                "volume": volume_val,
                "amount": amount_val,
                "pct_change": pct_change,
                "turnover_rate": turnover_rate,
                "prev_close": prev_close_val,
            }
        except (ValueError, IndexError) as e:
            logger.debug(f"解析 {stock_code} 数据失败: {e}")
            return None

    def fetch_daily_data(self, trade_date: date) -> list[dict[str, Any]]:
        """从新浪财经接口获取全市场股票日线数据

        流程：
        1. 通过 AKShare 获取股票代码列表
        2. 分批从新浪接口拉取行情数据
        3. 解析并返回统一格式
        """
        # 1. 获取股票列表
        logger.info("获取股票代码列表...")
        try:
            stock_list = ak.stock_info_a_code_name()
        except Exception as e:
            raise RuntimeError(f"获取股票列表失败: {e}") from e

        codes = stock_list["code"].tolist()
        logger.info(f"共 {len(codes)} 只股票，开始分批拉取行情...")

        all_data = []
        total_batches = (len(codes) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(codes), BATCH_SIZE):
            batch = codes[i:i + BATCH_SIZE]
            sina_codes = ",".join(self._sina_code(c) for c in batch)
            url = f"https://hq.sinajs.cn/list={sina_codes}"

            try:
                resp = self._session.get(url, timeout=30)
                resp.encoding = "gbk"
                text = resp.text
            except Exception as e:
                logger.warning(f"批次 {i // BATCH_SIZE + 1}/{total_batches} 请求失败: {e}")
                continue

            # 解析每一行
            for line in text.strip().split("\n"):
                if not line.strip():
                    continue
                parsed = self._parse_sina_line(line, trade_date)
                if parsed:
                    all_data.append(parsed)

            # 进度日志
            batch_num = i // BATCH_SIZE + 1
            if batch_num % 20 == 0 or batch_num == total_batches:
                logger.info(f"进度: {batch_num}/{total_batches} 批, 已收集 {len(all_data)} 条")

            # 控制请求频率
            if i + BATCH_SIZE < len(codes):
                time.sleep(REQUEST_INTERVAL)

        logger.info(f"数据获取完成，有效数据 {len(all_data)} 条")
        return all_data
