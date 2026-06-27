#!/bin/bash
# 回填30个交易日历史数据
# 用法: ./backfill.sh

set -e

API="http://localhost:8000/api/fetch"
DELAY=60  # 每次抓取间隔秒数（Tushare免费版限流保护）

echo "=== 回填历史数据 ==="
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "间隔: ${DELAY}s/天"
echo ""

# 生成 4/27 到 6/15 之间所有交易日（周一至周五）
dates=$(python3 -c "
from datetime import date, timedelta
d = date(2026, 4, 27)
end = date(2026, 6, 16)
while d < end:
    if d.weekday() < 5:
        print(d.isoformat())
    d += timedelta(days=1)
")

total=$(echo "$dates" | wc -l)
current=0

for dt in $dates; do
    current=$((current + 1))
    echo "[$current/$total] 抓取 $dt ..."

    resp=$(curl -s -X POST "$API?date=$dt")

    if echo "$resp" | grep -q '"skipped":true'; then
        count=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('raw_count','?'))" 2>/dev/null || echo "?")
        echo "  → 已存在 ($count 条)，跳过"
    elif echo "$resp" | grep -q '"detail"'; then
        err=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail','unknown'))" 2>/dev/null || echo "error")
        echo "  → 失败: $err"
    else
        count=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('raw_count','?'))" 2>/dev/null || echo "?")
        echo "  → 成功 ($count 条)"
    fi

    if [ $current -lt $total ]; then
        echo "  等待 ${DELAY}s..."
        sleep $DELAY
    fi
done

echo ""
echo "=== 回填完成 ==="
echo "结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "当前交易日:"
curl -s "http://localhost:8000/api/dates" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'共 {len(d[\"dates\"])} 天: {d[\"dates\"]}')"
