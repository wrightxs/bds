"""AKShare 数据源实现

当日数据：使用新浪批量行情接口 (hq.sinajs.cn)，一次拉取全市场。
历史数据：使用 AKShare stock_zh_a_daily 逐只查询新浪历史接口，
通过线程池并发提速（5 并发 + 0.5s 间隔），约 10 分钟回填一天。
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any

import akshare as ak
import pandas as pd
import requests

from app.fetcher.base import BaseFetcher

logger = logging.getLogger(__name__)

# 新浪实时行情接口，每次最多请求约 80 只股票
BATCH_SIZE = 80
REQUEST_INTERVAL = 0.3

# 历史数据并发数（避免被封 IP）
HIST_CONCURRENCY = 5
HIST_BATCH_DELAY = 0.5


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

    # ── 实时行情（当日） ──────────────────────────────────────

    def _sina_code(self, stock_code: str) -> str:
        """将纯数字代码转为新浪格式（sh600000 / sz000001）"""
        if stock_code.startswith(("60", "68")):
            return f"sh{stock_code}"
        else:
            return f"sz{stock_code}"

    def _parse_sina_line(self, line: str, trade_date: date) -> dict[str, Any] | None:
        """解析新浪实时行情单行数据"""
        match = re.search(r'hq_str_(\w+)="(.+)"', line)
        if not match:
            return None

        sina_code = match.group(1)
        fields = match.group(2).split(",")
        if len(fields) < 32:
            return None

        stock_code = sina_code[2:]

        try:
            name = fields[0]
            open_price = fields[1]
            prev_close = fields[2]
            current = fields[3]
            high = fields[4]
            low = fields[5]
            volume = fields[8]
            amount = fields[9]

            open_val = float(open_price) if open_price else None
            close_val = float(current) if current else None
            high_val = float(high) if high else None
            low_val = float(low) if low else None
            prev_close_val = float(prev_close) if prev_close else None
            volume_val = int(float(volume)) if volume else None
            amount_val = float(amount) if amount else None

            if close_val and prev_close_val and prev_close_val > 0:
                pct_change = round((close_val / prev_close_val - 1) * 100, 2)
            else:
                pct_change = None

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
                "turnover_rate": None,
                "prev_close": prev_close_val,
            }
        except (ValueError, IndexError) as e:
            logger.debug(f"解析 {stock_code} 数据失败: {e}")
            return None

    def _fetch_realtime(self, trade_date: date) -> list[dict[str, Any]]:
        """批量拉取新浪实时行情（仅用于当日）"""
        logger.info("获取股票代码列表...")
        try:
            stock_list = ak.stock_info_a_code_name()
        except Exception as e:
            raise RuntimeError(f"获取股票列表失败: {e}") from e

        codes = stock_list["code"].tolist()
        logger.info(f"共 {len(codes)} 只股票，开始分批拉取实时行情...")

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

            for line in text.strip().split("\n"):
                if not line.strip():
                    continue
                parsed = self._parse_sina_line(line, trade_date)
                if parsed:
                    all_data.append(parsed)

            batch_num = i // BATCH_SIZE + 1
            if batch_num % 20 == 0 or batch_num == total_batches:
                logger.info(f"实时行情进度: {batch_num}/{total_batches} 批, {len(all_data)} 条")

            if i + BATCH_SIZE < len(codes):
                time.sleep(REQUEST_INTERVAL)

        logger.info(f"实时行情获取完成，有效数据 {len(all_data)} 条")
        return all_data

    # ── 历史数据（回填） ──────────────────────────────────────

    def _fetch_one_historical(
        self, code: str, name: str, trade_date: date
    ) -> dict[str, Any] | None:
        """查询单只股票的历史日线数据

        查询 target_date-1 到 target_date 共 2 天，用于计算涨跌幅。
        """
        symbol = self._sina_code(code)
        start = (trade_date - timedelta(days=4)).strftime("%Y%m%d")  # 多取几天容错
        end = trade_date.strftime("%Y%m%d")

        try:
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust="")
        except Exception as e:
            logger.debug(f"{code} {name} 历史数据请求失败: {e}")
            return None

        if df is None or df.empty:
            return None

        # date 列可能是 str 或 datetime
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # 取目标日期的数据
        row = df[df["date"] == trade_date]
        if row.empty:
            return None
        row = row.iloc[0]

        # 取前一日收盘价（用于计算涨跌幅）
        prev_rows = df[df["date"] < trade_date].sort_values("date", ascending=False)
        prev_close = float(prev_rows.iloc[0]["close"]) if not prev_rows.empty else None

        close_val = float(row["close"])
        open_val = float(row["open"])
        high_val = float(row["high"])
        low_val = float(row["low"])
        volume_val = int(row["volume"])
        amount_val = float(row["amount"])
        turnover_val = float(row["turnover"]) if pd.notna(row.get("turnover")) else None

        if close_val <= 0:
            return None

        if prev_close and prev_close > 0:
            pct_change = round((close_val / prev_close - 1) * 100, 2)
        else:
            pct_change = None

        return {
            "trade_date": trade_date,
            "stock_code": code,
            "stock_name": name,
            "open": open_val,
            "close": close_val,
            "high": high_val,
            "low": low_val,
            "volume": volume_val,
            "amount": amount_val,
            "pct_change": pct_change,
            "turnover_rate": turnover_val,
            "prev_close": prev_close,
        }

    def _fetch_historical(self, trade_date: date) -> list[dict[str, Any]]:
        """逐只拉取历史数据（线程池并发）

        用于回填非当日的交易数据，耗时约 8-15 分钟/天。
        """
        logger.info("获取股票代码列表...")
        try:
            stock_list = ak.stock_info_a_code_name()
        except Exception as e:
            raise RuntimeError(f"获取股票列表失败: {e}") from e

        code_name_map = dict(zip(stock_list["code"], stock_list["name"]))
        codes = list(code_name_map.keys())
        logger.info(f"共 {len(codes)} 只股票，开始逐只拉取历史数据（并发={HIST_CONCURRENCY}）...")

        all_data = []
        completed = 0
        last_log = 0

        with ThreadPoolExecutor(max_workers=HIST_CONCURRENCY) as executor:
            futures = {
                executor.submit(
                    self._fetch_one_historical, code, code_name_map[code], trade_date
                ): code
                for code in codes
            }

            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result()
                    if result:
                        all_data.append(result)
                except Exception as e:
                    logger.debug(f"股票 {futures[future]} 处理异常: {e}")

                # 每 200 只打印一次进度
                if completed - last_log >= 200 or completed == len(codes):
                    logger.info(
                        f"历史数据进度: {completed}/{len(codes)} 只, "
                        f"有效 {len(all_data)} 条"
                    )
                    last_log = completed

                # 每批之间短暂延迟
                if completed % HIST_CONCURRENCY == 0:
                    time.sleep(HIST_BATCH_DELAY)

        logger.info(f"历史数据获取完成，有效数据 {len(all_data)} 条")
        return all_data

    # ── 行业分类同步 ──────────────────────────────────────────

    def fetch_stock_industry(self) -> dict[str, str]:
        """获取全量股票→行业分类映射

        通过东方财富行业板块接口，遍历所有行业板块获取成分股，
        构建 stock_code → industry_name 的映射字典。
        行业分类数据较稳定，建议首次抓取后缓存到 stock_info 表。
        """
        import akshare as ak

        logger.info("开始获取行业分类数据...")
        try:
            industry_df = ak.stock_board_industry_name_em()
        except Exception as e:
            logger.warning(f"获取行业板块列表失败: {e}")
            return {}

        industry_names = industry_df["板块名称"].tolist()
        logger.info(f"共 {len(industry_names)} 个行业板块，开始获取成分股...")

        code_industry: dict[str, str] = {}
        for idx, name in enumerate(industry_names):
            try:
                cons_df = ak.stock_board_industry_cons_em(symbol=name)
                for _, row in cons_df.iterrows():
                    code = str(row["代码"]).zfill(6)
                    # 同一个股票可能属于多个板块，保留第一个
                    if code not in code_industry:
                        code_industry[code] = name
            except Exception as e:
                logger.debug(f"获取板块 '{name}' 成分股失败: {e}")
                continue

            if (idx + 1) % 20 == 0:
                logger.info(f"行业分类进度: {idx + 1}/{len(industry_names)}, 已映射 {len(code_industry)} 只")

            time.sleep(0.15)  # 控制频率

        logger.info(f"行业分类获取完成，共 {len(code_industry)} 只股票有行业映射")
        return code_industry

    # ── 统一入口 ──────────────────────────────────────────────

    def fetch_daily_data(self, trade_date: date) -> list[dict[str, Any]]:
        """获取指定交易日全市场股票数据

        - 当日或未来日期 → 使用新浪批量实时接口（快，约 30 秒）
        - 历史日期 → 使用新浪历史接口逐只查询（慢，约 10 分钟）
        """
        today = date.today()
        if trade_date >= today:
            logger.info(f"{trade_date} 非历史日期，使用实时行情接口")
            return self._fetch_realtime(trade_date)
        else:
            logger.info(f"{trade_date} 为历史日期，使用历史数据接口（较慢）")
            return self._fetch_historical(trade_date)
