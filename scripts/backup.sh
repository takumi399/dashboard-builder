#!/bin/bash
# 定时备份脚本，配合 cron 使用
# 用法: DATABASE_URL=postgresql://user:pass@host:5432/db ./scripts/backup.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

if [ -z "$DATABASE_URL" ]; then
    echo "错误: DATABASE_URL 环境变量未设置"
    exit 1
fi

if [[ "$DATABASE_URL" == postgresql* ]] || [[ "$DATABASE_URL" == postgres* ]]; then
    # PostgreSQL: 使用 pg_dump
    echo "[$(date)] 开始 PostgreSQL 备份..."

    # 解析 DATABASE_URL
    # 格式: postgresql://user:password@host:port/dbname
    DB_URL="${DATABASE_URL#*://}"
    AUTH="${DB_URL%%@*}"
    HOST_PORT_DB="${DB_URL#*@}"
    HOST_PORT="${HOST_PORT_DB%%/*}"
    DBNAME="${HOST_PORT_DB#*/}"

    USER="${AUTH%%:*}"
    PASSWORD="${AUTH#*:}"
    HOST="${HOST_PORT%%:*}"
    PORT="${HOST_PORT#*:}"

    export PGPASSWORD="$PASSWORD"
    pg_dump -h "$HOST" -p "${PORT:-5432}" -U "$USER" -d "$DBNAME" > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

    if [ $? -eq 0 ]; then
        echo "[$(date)] PostgreSQL 备份完成: $BACKUP_DIR/backup_$TIMESTAMP.sql"
    else
        echo "[$(date)] PostgreSQL 备份失败!"
    fi

elif [[ "$DATABASE_URL" == sqlite* ]]; then
    # SQLite: 直接复制文件
    echo "[$(date)] 开始 SQLite 备份..."
    DB_PATH="${DATABASE_URL#sqlite+aiosqlite:///}"
    DB_PATH="${DB_PATH#sqlite:///}"
    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "$BACKUP_DIR/backup_$TIMESTAMP.db"
        echo "[$(date)] SQLite 备份完成: $BACKUP_DIR/backup_$TIMESTAMP.db"
    else
        echo "[$(date)] SQLite 备份失败: 文件 $DB_PATH 不存在"
        exit 1
    fi
else
    echo "[$(date)] 不支持的数据库类型: $DATABASE_URL"
    exit 1
fi

# 保留最近 7 天的备份
find "$BACKUP_DIR" -name "backup_*" -mtime +7 -delete
echo "[$(date)] 已清理 7 天前的旧备份"

echo "[$(date)] 备份任务完成"
