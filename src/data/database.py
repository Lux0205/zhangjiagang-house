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
    1. raw_prices  — 原始抓取的每套房屋价格（含 community_type、data_type 字段）
    2. ohlc_data   — 聚合后的OHLC K线数据（按 区域+类型+日期+data_type 聚合）

    data_type: 'buy'=买房(元/㎡), 'rent'=租房(元/月)

    注意：SQLite 的 ALTER TABLE ADD COLUMN 无法修改 UNIQUE 约束，
    因此旧表迁移时需要通过"新建表→复制数据→删除旧表→重命名"来刷新约束。
    """
    conn = get_connection()
    c = conn.cursor()

    # 第一步：创建新表（包含 community_type、data_type 列）
    c.execute("""
        CREATE TABLE IF NOT EXISTS raw_prices (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            region          TEXT    NOT NULL,
            community       TEXT,
            community_type  TEXT    DEFAULT '高层',
            data_type       TEXT    DEFAULT 'buy',
            price           REAL    NOT NULL,
            unit            TEXT    DEFAULT '元/㎡',
            source          TEXT    NOT NULL,
            fetch_time      TEXT    NOT NULL,
            UNIQUE(date, region, community, source, data_type)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ohlc_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            region          TEXT    NOT NULL,
            community_type  TEXT    DEFAULT '高层',
            data_type       TEXT    DEFAULT 'buy',
            open_price      REAL,
            high_price      REAL,
            low_price       REAL,
            close_price     REAL,
            avg_price       REAL,
            volume          INTEGER DEFAULT 0,
            sources         TEXT,
            updated_at      TEXT    NOT NULL,
            UNIQUE(date, region, community_type, data_type)
        )
    """)

    # 第二步：检查并升级旧表
    # SQLite 的 ALTER TABLE ADD COLUMN 无法修改 UNIQUE 约束，
    # 所以需要检测旧约束并重建表以刷新约束定义。
    _migrate_table(c, "raw_prices",
                   "(date, region, community, source, data_type)",
                   ["community_type", "data_type"])
    _migrate_table(c, "ohlc_data",
                   "(date, region, community_type, data_type)",
                   ["community_type", "data_type"])

    # 索引
    c.execute("CREATE INDEX IF NOT EXISTS idx_rp_drtd ON raw_prices(date, region, community_type, data_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_od_drtd ON ohlc_data(date, region, community_type, data_type)")

    conn.commit()
    logger.info("数据库初始化完成")
    conn.close()


def _migrate_table(cursor, table_name, expected_unique_cols, expected_columns):
    """
    迁移单张表：通过"重命名旧表→新建正确表→复制数据→删除旧表"的方式
    修复 SQLite 的 ALTER TABLE ADD COLUMN 无法更新 UNIQUE 约束的问题。

    参数:
        cursor: 数据库游标
        table_name: 表名
        expected_unique_cols: 期望的 UNIQUE 约束列（仅用于日志）
        expected_columns: 必须存在的列名列表（用于判断是否需要迁移）
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [row[1] for row in cursor.fetchall()]

    # 检查是否缺少新列（说明是旧版数据库）
    missing_cols = [col for col in expected_columns if col not in existing_cols]
    if not missing_cols:
        logger.info(f"{table_name} 结构已是最新，无需迁移")
        return

    logger.info(f"{table_name} 旧版数据库缺少列 {missing_cols}，执行完整迁移...")

    # 读取旧数据
    cursor.execute(f"SELECT * FROM {table_name}")
    old_rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description] if cursor.description else []

    # 重命名旧表（保留数据）
    cursor.execute(f"ALTER TABLE {table_name} RENAME TO _migrate_old_{table_name}")

    # 创建新表（使用正确的含 data_type 的 UNIQUE 约束）
    if table_name == "raw_prices":
        cursor.execute("""
            CREATE TABLE raw_prices (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT    NOT NULL,
                region          TEXT    NOT NULL,
                community       TEXT,
                community_type  TEXT    DEFAULT '高层',
                data_type       TEXT    DEFAULT 'buy',
                price           REAL    NOT NULL,
                unit            TEXT    DEFAULT '元/㎡',
                source          TEXT    NOT NULL,
                fetch_time      TEXT    NOT NULL,
                UNIQUE(date, region, community, source, data_type)
            )
        """)
    elif table_name == "ohlc_data":
        cursor.execute("""
            CREATE TABLE ohlc_data (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT    NOT NULL,
                region          TEXT    NOT NULL,
                community_type  TEXT    DEFAULT '高层',
                data_type       TEXT    DEFAULT 'buy',
                open_price      REAL,
                high_price      REAL,
                low_price       REAL,
                close_price     REAL,
                avg_price       REAL,
                volume          INTEGER DEFAULT 0,
                sources         TEXT,
                updated_at      TEXT    NOT NULL,
                UNIQUE(date, region, community_type, data_type)
            )
        """)

    # 将旧数据回填新表（data_type 默认 buy）
    for row in old_rows:
        row_dict = dict(zip(col_names, row)) if col_names else {}
        if table_name == "raw_prices":
            cursor.execute("""
                INSERT INTO raw_prices
                (date, region, community, community_type, data_type,
                 price, unit, source, fetch_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row_dict.get("date", ""),
                row_dict.get("region", ""),
                row_dict.get("community", ""),
                row_dict.get("community_type", "高层"),
                "buy",
                row_dict.get("price", 0),
                row_dict.get("unit", "元/㎡"),
                row_dict.get("source", ""),
                row_dict.get("fetch_time", ""),
            ))
        elif table_name == "ohlc_data":
            cursor.execute("""
                INSERT INTO ohlc_data
                (date, region, community_type, data_type,
                 open_price, high_price, low_price, close_price,
                 avg_price, volume, sources, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row_dict.get("date", ""),
                row_dict.get("region", ""),
                row_dict.get("community_type", "高层"),
                "buy",
                row_dict.get("open_price"),
                row_dict.get("high_price"),
                row_dict.get("low_price"),
                row_dict.get("close_price"),
                row_dict.get("avg_price"),
                row_dict.get("volume", 0),
                row_dict.get("sources", ""),
                row_dict.get("updated_at", ""),
            ))

    # 删除旧表
    cursor.execute(f"DROP TABLE IF EXISTS _migrate_old_{table_name}")

    logger.info(f"{table_name} 迁移完成: {len(old_rows)} 条旧数据已回填，"
                f"UNIQUE 约束已更新为 {expected_unique_cols}")


# ===== 原始价格操作 =====

def insert_raw_price(date, region, community, price, source,
                     unit="元/㎡", community_type="高层", data_type="buy"):
    """
    插入一条原始价格。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO raw_prices
            (date, region, community, community_type, data_type, price, unit, source, fetch_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, region, community, community_type, data_type, price, unit, source,
              datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"插入失败: {e}")
        return False
    finally:
        conn.close()


def insert_raw_prices_batch(records):
    """
    批量插入原始价格数据。

    参数:
        records: 字典列表，每个字典需包含 date, region, price, source，
                 可选 community, community_type, data_type, unit
    """
    conn = get_connection()
    count = 0
    try:
        now = datetime.now().isoformat()
        for r in records:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO raw_prices
                    (date, region, community, community_type, data_type, price, unit, source, fetch_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["date"], r["region"], r.get("community", ""),
                    r.get("community_type", "高层"),
                    r.get("data_type", "buy"),
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


def get_raw_prices(date, region, community_type=None, data_type="buy"):
    """
    查询原始价格数据。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    conn = get_connection()
    try:
        if community_type:
            cur = conn.execute("""
                SELECT * FROM raw_prices
                WHERE date=? AND region=? AND community_type=? AND data_type=?
                ORDER BY price
            """, (date, region, community_type, data_type))
        else:
            cur = conn.execute("""
                SELECT * FROM raw_prices WHERE date=? AND region=? AND data_type=?
                ORDER BY price
            """, (date, region, data_type))
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
                avg_price, volume, sources="", data_type="buy"):
    """
    插入/更新OHLC数据。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO ohlc_data
            (date, region, community_type, data_type, open_price, high_price, low_price,
             close_price, avg_price, volume, sources, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, region, community_type, data_type, open_price, high_price, low_price,
              close_price, avg_price, volume, sources, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"插入OHLC失败: {e}")
        return False
    finally:
        conn.close()


def get_ohlc_by_region_type(region, community_type, days=365, data_type="buy"):
    """
    查询某区域某类型最近N天的OHLC数据。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    conn = get_connection()
    try:
        cur = conn.execute("""
            SELECT date, open_price, high_price, low_price, close_price,
                   avg_price, volume, sources
            FROM ohlc_data
            WHERE region=? AND community_type=? AND data_type=?
              AND date >= date('now', ?)
            ORDER BY date ASC
        """, (region, community_type, data_type, f"-{days} days"))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_latest_ohlc(region, community_type, data_type="buy"):
    """
    查询某区域某类型最新的OHLC数据。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    conn = get_connection()
    try:
        cur = conn.execute("""
            SELECT date, open_price, high_price, low_price, close_price,
                   avg_price, volume, sources
            FROM ohlc_data
            WHERE region=? AND community_type=? AND data_type=?
            ORDER BY date DESC LIMIT 1
        """, (region, community_type, data_type))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_last_update_time(data_type="buy"):
    """
    获取某种数据类型最后更新日期。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    conn = get_connection()
    try:
        cur = conn.execute("SELECT MAX(date) as last_date FROM ohlc_data WHERE data_type=?", (data_type,))
        row = cur.fetchone()
        return row["last_date"] if row else None
    finally:
        conn.close()


# ===== 初始化 =====
init_database()
