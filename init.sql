-- 股票每日原始数据表
CREATE TABLE IF NOT EXISTS stock_daily_raw (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票名称',
    open DECIMAL(10, 3) COMMENT '开盘价',
    close DECIMAL(10, 3) COMMENT '收盘价',
    high DECIMAL(10, 3) COMMENT '最高价',
    low DECIMAL(10, 3) COMMENT '最低价',
    volume BIGINT COMMENT '成交量（股）',
    amount DECIMAL(16, 2) COMMENT '成交额（元）',
    pct_change DECIMAL(6, 2) COMMENT '涨跌幅（%）',
    turnover_rate DECIMAL(6, 2) COMMENT '换手率（%）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_date_amount (trade_date, amount DESC),
    INDEX idx_date_pct (trade_date, pct_change DESC),
    UNIQUE KEY uk_date_code (trade_date, stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票每日原始数据';

-- 每日成交额前100股票表
CREATE TABLE IF NOT EXISTS stock_top100 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    `rank` INT NOT NULL COMMENT '排名（1-100）',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票名称',
    amount DECIMAL(16, 2) COMMENT '成交额（元）',
    pct_change DECIMAL(6, 2) COMMENT '涨跌幅（%）',
    close DECIMAL(10, 3) COMMENT '收盘价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_date_rank (trade_date, `rank`),
    UNIQUE KEY uk_date_rank (trade_date, `rank`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日成交额前100股票';

-- 每日涨停股票表
CREATE TABLE IF NOT EXISTS stock_limit_up (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date DATE NOT NULL COMMENT '交易日期',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票名称',
    limit_up_price DECIMAL(10, 3) COMMENT '涨停价',
    board VARCHAR(20) NOT NULL COMMENT '板块（主板/创业板/科创板/北交所）',
    pct_change DECIMAL(6, 2) COMMENT '涨跌幅（%）',
    consecutive INT DEFAULT 1 COMMENT '连板天数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_date_code (trade_date, stock_code),
    INDEX idx_date_board (trade_date, board)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日涨停股票';
