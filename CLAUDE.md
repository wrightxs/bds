# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

BDS (Big Data Stock) — A股每日数据统计系统。每个交易日 18:00 自动抓取全市场数据，统计成交额前100和涨停股票，前端展示。

后端 Python 3.11 + FastAPI + SQLAlchemy + APScheduler，前端 Vue 3 + Vite + Tailwind CSS，数据库 MySQL 8.0，Docker Compose 部署。数据源默认 AKShare，后期可切换 Tushare。

## 常用命令

```bash
# 启动全部服务
docker-compose up -d

# 后端开发（本地）
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端开发（本地）
cd frontend && npm install && npm run dev     # 访问 http://localhost:3000，API 代理到 8000

# 手动触发数据抓取
curl -X POST "http://localhost:8000/api/fetch"                    # 今天
curl -X POST "http://localhost:8000/api/fetch?date=2026-06-17"    # 指定日期

# 验证 API
curl "http://localhost:8000/api/health"
curl "http://localhost:8000/api/dashboard"
curl "http://localhost:8000/api/top100"
curl "http://localhost:8000/api/limit_up?board=main"
```

API 文档：`http://localhost:8000/docs`

## 核心架构

### 数据流

```
AKShare API (stock_zh_a_spot_em)
  → fetcher/ (BaseFetcher → AKShareFetcher)          # 数据获取，返回统一格式
  → stock_daily_raw                                   # 原始数据入库
  → service/top100.py → stock_top100                  # 按成交额排序取前100
  → service/limit_up.py → stock_limit_up              # 涨停识别 + 板块分类 + 连板计算
  → router/ → JSON API → Vue 前端
```

### 涨停判断 (`backend/app/service/limit_up.py`)

根据股票代码前缀判定板块，不同板块涨停阈值不同（EPSILON=0.005 容差）：

| 板块 | 代码前缀 | 阈值 |
|------|---------|------|
| 主板 | 60xxxx, 00xxxx | 9.97% |
| 创业板 | 30xxxx | 19.97% |
| 科创板 | 68xxxx | 19.97% |
| 北交所 | 83xxxx, 43xxxx | 29.97% |

前收盘价通过 `close / (1 + pct_change/100)` 反推。连板天数通过查询前一个交易日的 `stock_limit_up` 表累加得出。

### 数据源切换

`fetcher/__init__.py` 中的 `get_fetcher()` 工厂函数根据环境变量 `DATA_SOURCE`（默认 `akshare`）返回对应实现。新增数据源只需继承 `BaseFetcher` 实现 `fetch_daily_data` 方法。

### 定时任务 (`backend/app/scheduler.py`)

APScheduler 工作日（周一至周五）18:00 触发。包含幂等保护（当日数据已存在则跳过）。时间可通过 `SCHEDULE_HOUR` / `SCHEDULE_MINUTE` 环境变量调整。`POST /api/fetch?date=` 提供手动触发和回填能力。

### 前端路由与组件

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard.vue | 市场总成交额、涨停数、榜首股票，前5预览 |
| `/top100` | Top100.vue | 可排序表格（排名/代码/名称/收盘价/成交额/涨跌幅） |
| `/limit-up` | LimitUp.vue | BoardFilter 板块筛选 + StockTable（含连板徽章） |

`StockTable.vue` 是通用表格组件，通过 `columns` prop 定义列，内置成交额/百分比/价格格式化，红涨绿跌着色。`BoardFilter.vue` 提供全部/主板/创业板/科创板/北交所五个筛选按钮。

## 数据库

表定义见 `init.sql`（容器启动自动执行），ORM 模型见 `backend/app/models.py`。三张表均以 `trade_date` 为核心查询维度：

- **stock_daily_raw** — 全市场每日原始行情（唯一键 `trade_date + stock_code`）
- **stock_top100** — 成交额前100快照（唯一键 `trade_date + rank`）
- **stock_limit_up** — 涨停股票快照（唯一键 `trade_date + stock_code`，含 `board` 和 `consecutive` 字段）

表结构变更时，同步更新 `init.sql` 和 `models.py` 两处。

## 操作规范

- **覆盖文件前先备份**：修改系统文件（如 `/etc/docker/daemon.json`）或通过重定向覆盖已有文件前，先用 `cp` 备份原文件（如 `cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d)`），再执行覆盖操作。
