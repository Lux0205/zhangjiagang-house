"""
张家港房价App - SQLite 数据库操作模块
管理房价数据的存储和查询
支持按小区类型（别墅/洋房/拆迁房/老小区/高层）分类
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from src.utils.config import DATABASE_PATH, COMMUNITY_TYPES
from src.utils.logger import get_logger

logger = get_logger("database")


def get_connection() -> sqlite3.Connection:
    """获取数据库连接，自动创建目录和表"""
    db_dir = os.path.dirname(DATABASE_PATH)
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_database():
    """
    初始化数据库表结构。
    两张表：
    1. raw_prices  — 原始抓取的每套房屋价格（增加 community_type 字段）
    2. ohlc_data   — 聚合后的OHLC K线数据（按 区域+类型+日期 聚合）
    """
    conn = get_connection()
    c = conn.cursor()

    # 第一步：创建新表（包含 community_type 列）
    c.execute("""
        CREATE TABLE IF NOT EXISTS raw_prices (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            region          TEXT    NOT NULL,
            community       TEXT,
            community_type  TEXT    DEFAULT '高层',
            price           REAL    NOT NULL,
            unit            TEXT    DEFAULT '元/㎡',
            source          TEXT    NOT NULL,
            fetch_time      TEXT    NOT NULL,
            UNIQUE(date, region, community, source)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ohlc_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            region          TEXT    NOT NULL,
            community_type  TEXT    DEFAULT '高层',
            open_price      REAL,
            high_price      REAL,
            low_price       REAL,
            close_price     REAL,
            avg_price       REAL,
            volume          INTEGER DEFAULT 0,
            sources         TEXT,
            updated_at      TEXT    NOT NULL,
            UNIQUE(date, region, community_type)
        )
    """)

    # 第二步：检查是否需要升级旧表（已有表但没有 community_type 列）
    c.execute("PRAGMA table_info(raw_prices)")
    raw_cols = [row[1] for row in c.fetchall()]
    if "community_type" not in raw_cols:
        c.execute("ALTER TABLE raw_prices ADD COLUMN community_type TEXT DEFAULT '高层'")
        logger.info("raw_prices 表升级: 增加 community_type 列")

    c.execute("PRAGMA table_info(ohlc_data)")
    ohlc_cols = [row[1] for row in c.fetchall()]
    if "community_type" not in ohlc_cols:
        c.execute("ALTER TABLE ohlc_data ADD COLUMN community_type TEXT DEFAULT '高层'")
        logger.info("ohlc_data 表升级: 增加 community_type 列")

    # 索引
    c.execute("CREATE INDEX IF NOT EXISTS idx_rp_dr ON raw_prices(date, region)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rp_drt ON raw_prices(date, region, community_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_od_dr ON ohlc_data(date, region)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_od_drt ON ohlc_data(date, region, community_type)")

    conn.commit()
    logger.info("数据库初始化完成")
    conn.close()


# ===== 原始价格操作 =====

def insert_raw_price(date, region, community, price, source,
                     unit="元/㎡", community_type="高层"):
    """插入一条原始价格"""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO raw_prices
            (date, region, community, community_type, price, unit, source, fetch_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, region, community, community_type, price, unit, source,
              datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"插入失败: {e}")
        return False
    finally:
        conn.close()


def insert_raw_prices_batch(records):
    """批量插入原始价格数据"""
    conn = get_connection()
    count = 0
    try:
        now = datetime.now().isoformat()
        for r in records:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO raw_prices
                    (date, region, community, community_type, price, unit, source, fetch_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["date"], r["region"], r.get("community", ""),
                    r.get("community_type", "高层"),
                    r["price"], r.get("unit", "元/㎡"), r["source"], now
                ))
                count += 1
            except (sqlite3.Error, KeyError) as e:
                logger.warning(f"跳过一条: {e}")
        conn.commit()
        logger.info(f"批量插入 {count} 条原始数据")
    except sqlite3.Error as e:
        logger.error(f"批量插入失败: {e}")
    finally:
        conn.close()
    return count


def get_raw_prices(date, region, community_type=None):
    """查询原始价格数据"""
    conn = get_connection()
    try:
        if community_type:
            cur = conn.execute("""
                SELECT * FROM raw_prices
                WHERE date=? AND region=? AND community_type=?
                ORDER BY price
            """, (date, region, community_type))
        else:
            cur = conn.execute("""
                SELECT * FROM raw_prices WHERE date=? AND region=?
                ORDER BY price
            """, (date, region))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_raw_prices_stats(date, region):
    """按小区类型分组统计数据量"""
    conn = get_connection()
    try:
        cur = conn.execute("""
            SELECT community_type, COUNT(*) as cnt,
                   MIN(price) as min_p, MAX(price) as max_p,
                   AVG(price) as avg_p
            FROM raw_prices
            WHERE date=? AND region=?
            GROUP BY community_type
            ORDER BY avg_p DESC
        """, (date, region))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ===== OHLC 数据操作 =====

def insert_ohlc(date, region, community_type,
                open_price, high_price, low_price, close_price,
                avg_price, volume, sources=""):
    """插入/更新OHLC数据"""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO ohlc_data
            (date, region, community_type, open_price, high_price, low_price,
             close_price, avg_price, volume, sources, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, region, community_type, open_price, high_price, low_price,
              close_price, avg_price, volume, sources, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"插入OHLC失败: {e}")
        return False
    finally:
        conn.close()


def get_ohlc_by_region_type(region, community_type, days=365):
    """查询某区域某类型最近N天的OHLC数据"""
    conn = get_connection()
    try:
        cur = conn.execute("""
            SELECT date, open_price, high_price, low_price, close_price,
                   avg_price, volume, sources
            FROM ohlc_data
            WHERE region=? AND community_type=?
              AND date >= date('now', ?)
            ORDER BY date ASC
        """, (region, community_type, f"-{days} days"))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_latest_ohlc(region, community_type):
    """查询某区域某类型最新的OHLC数据"""
    conn = get_connection()
    try:
        cur = conn.execute("""
            SELECT date, open_price, high_price, low_price, close_price,
                   avg_price, volume, sources
            FROM ohlc_data
            WHERE region=? AND community_type=?
            ORDER BY date DESC LIMIT 1
        """, (region, community_type))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_last_update_time():
    """获取最后更新日期"""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT MAX(date) as last_date FROM ohlc_data")
        row = cur.fetchone()
        return row["last_date"] if row else None
    finally:
        conn.close()


# ===== 初始化 =====
init_database()
