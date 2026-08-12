"""
测试完整数据流程：爬虫 → 数据库 → 聚合 → 图表
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from src.scraper.fang import FangScraper
from src.data.database import (
    insert_raw_prices_batch, get_connection, init_database,
    get_ohlc_by_region_type
)
from src.utils.aggregator import aggregate_daily_prices, get_chart_data
from src.utils.config import REGION_NAMES, COMMUNITY_TYPE_NAMES

print("=" * 60)
print("=== 测试完整数据流程 ===")
print("=" * 60)

# 步骤1: 运行爬虫
print("\n--- 步骤1: 运行房天下爬虫 ---")
scraper = FangScraper()
records = scraper.scrape()
print(f"抓取到 {len(records)} 条数据")

# 步骤2: 存入数据库
print("\n--- 步骤2: 存入数据库 ---")
count = insert_raw_prices_batch(records)
print(f"存入 {count} 条原始数据")

# 步骤3: 聚合OHLC
print("\n--- 步骤3: 聚合OHLC数据 ---")
today = datetime.now().strftime("%Y-%m-%d")
for region in REGION_NAMES:
    for ctype in COMMUNITY_TYPE_NAMES:
        aggregate_daily_prices(today, region, ctype, data_type="buy")

# 步骤4: 查询图表数据
print("\n--- 步骤4: 查询图表数据 ---")
for region in REGION_NAMES:
    for ctype in COMMUNITY_TYPE_NAMES[:2]:  # 只查前2个类型
        data = get_chart_data(region, ctype, days=30, data_type="buy")
        if data["latest"]:
            print(f"  [{region}] {ctype}: 均价 {data['latest']['close_price']} 元/㎡, "
                  f"数据天数 {len(data['dates'])}")
        else:
            print(f"  [{region}] {ctype}: 暂无数据")

# 步骤5: 统计数据库
print("\n--- 步骤5: 数据库统计 ---")
conn = get_connection()
cur = conn.execute("SELECT COUNT(*) FROM raw_prices WHERE data_type='buy'")
print(f"  买房原始数据: {cur.fetchone()[0]} 条")

cur = conn.execute("SELECT COUNT(*) FROM raw_prices WHERE data_type='rent'")
print(f"  租房原始数据: {cur.fetchone()[0]} 条")

cur = conn.execute("SELECT COUNT(*) FROM ohlc_data WHERE data_type='buy'")
print(f"  买房OHLC数据: {cur.fetchone()[0]} 条")

cur = conn.execute("SELECT COUNT(*) FROM ohlc_data WHERE data_type='rent'")
print(f"  租房OHLC数据: {cur.fetchone()[0]} 条")

# 检查OHLC完整性
cur = conn.execute(
    "SELECT DISTINCT region, community_type FROM ohlc_data WHERE data_type='buy'"
)
existing = {(row[0], row[1]) for row in cur.fetchall()}
expected = len(REGION_NAMES) * len(COMMUNITY_TYPE_NAMES)
print(f"  买房OHLC组合: {len(existing)}/{expected}")

missing = []
for r in REGION_NAMES:
    for t in COMMUNITY_TYPE_NAMES:
        if (r, t) not in existing:
            missing.append((r, t))
if missing:
    print(f"  缺失组合: {missing}")

conn.close()

print("\n=== 测试完成 ===")
