#!/bin/bash
# BDS 股票分析系统 — 一键部署脚本
# 用法: ./deploy.sh [服务器IP] [用户名]

set -e

SERVER_IP="${1:-}"
SERVER_USER="${2:-root}"

if [ -z "$SERVER_IP" ]; then
    echo "用法: ./deploy.sh <服务器IP> [用户名]"
    echo "示例: ./deploy.sh 123.45.67.89 root"
    exit 1
fi

PROJECT="bs"
REMOTE_DIR="/opt/$PROJECT"

echo "=== 1. 导出数据库 ==="
docker exec stock_mysql mysqldump -u root -proot123 stock_analysis \
    --single-transaction --no-tablespaces \
    > mysql_data.sql 2>/dev/null
echo "数据库导出完成: $(du -h mysql_data.sql | cut -f1)"

echo "=== 2. 打包项目 ==="
tar czf /tmp/$PROJECT.tar.gz \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='mysql_data' \
    --exclude='mysql_dump.sql' \
    -C /home/yuan/project/claude \
    $PROJECT/ 2>/dev/null
echo "打包完成: $(du -h /tmp/$PROJECT.tar.gz | cut -f1)"

echo "=== 3. 上传到服务器 ==="
scp /tmp/$PROJECT.tar.gz "$SERVER_USER@$SERVER_IP:/tmp/"
ssh "$SERVER_USER@$SERVER_IP" "
    mkdir -p $REMOTE_DIR &&
    tar xzf /tmp/${PROJECT}.tar.gz -C $REMOTE_DIR &&
    rm /tmp/${PROJECT}.tar.gz &&
    echo '解压完成'
"

echo "=== 4. 导入数据库并启动 ==="
ssh "$SERVER_USER@$SERVER_IP" "
    cd $REMOTE_DIR &&
    # 创建 .env 文件（替换 Tushare token 为你自己的）
    cat > .env << 'ENVEOF'
MYSQL_ROOT_PASSWORD=root123
MYSQL_DATABASE=stock_analysis
MYSQL_USER=stock_user
MYSQL_PASSWORD=stock_pass
DATA_SOURCE=tushare
TUSHARE_TOKEN=你的token
SCHEDULE_HOUR=18
SCHEDULE_MINUTE=0
ENVEOF
    # 启动服务
    docker-compose up -d &&
    sleep 10 &&
    # 导入数据
    docker exec -i stock_mysql mysql -u root -proot123 stock_analysis < mysql_data.sql &&
    echo '部署完成！访问 http://$SERVER_IP'
"

echo ""
echo "=== 部署完成 ==="
echo "后端 API: http://$SERVER_IP:8000/docs"
echo "前端页面: http://$SERVER_IP"
echo ""
echo "注意: 请修改 $REMOTE_DIR/.env 中的 TUSHARE_TOKEN 为你自己的 token"
