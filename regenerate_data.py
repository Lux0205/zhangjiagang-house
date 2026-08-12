"""
清理旧假数据，用新的真实基准价重新生成数据
基于房天下2026年8月张家港真实数据
"""
import sys
sys.path.insert(0, '.')

from src.data.database import get_connection
from src.utils.dummy_data import generate_dummy_data, fill_ohlc_from_dummy, ensure_data_available
from src.utils.config import DATA_TYPE_NAMES, DATA_TYPES

print("=" * 60)
print("=== 清理旧数据，用新基准价重新生成 ===")
print("=" * 60)

# 步骤1: 清理旧数据
print("\n--- 步骤1: 清理旧数据 ---")
conn = get_connection()
for dt in DATA_TYPE_NAMES:
    label = DATA_TYPES[dt]
    cur = conn.execute("DELETE FROM raw_prices WHERE data_type=?", (dt,))
    raw_deleted = cur.rowcount
    cur = conn.execute("DELETE FROM ohlc_data WHERE data_type=?", (dt,))
    ohlc_deleted = cur.rowcount
    print(f"  {label}: 删除 {raw_deleted} 条原始数据, {ohlc_deleted} 条OHLC数据")
conn.commit()
conn.close()

# 步骤2: 用新基准价生成假数据
print("\n--- 步骤2: 用新基准价生成假数据 ---")
for dt in DATA_TYPE_NAMES:
    label = DATA_TYPES[dt]
    print(f"\n  正在生成 {label} 数据...")
    count = generate_dummy_data(30, data_type=dt)
    print(f"  生成 {count} 条原始数据")
    fill_ohlc_from_dummy(data_type=dt)
    print(f"  OHLC聚合完成")

# 步骤3: 验证结果
print("\n--- 步骤3: 验证结果 ---")
from src.utils.aggregator import get_chart_data
from src.utils.config import REGION_NAMES, COMMUNITY_TYPE_NAMES

print("\n  买房价格预览（元/㎡）:")
print(f"  {'区域':<6} {'别墅':>10} {'洋房':>10} {'高层':>10} {'老小区':>10} {'拆迁房':>10}")
print("  " + "-" * 60)
for region in REGION_NAMES:
    prices = []
    for ctype in COMMUNITY_TYPE_NAMES:
        data = get_chart_data(region, ctype, days=30, data_type="buy")
        if data["latest"]:
            prices.append(f"{data['latest']['close_price']:>10.0f}")
        else:
            prices.append(f"{'N/A':>10}")
    print(f"  {region:<6} {prices[0]} {prices[1]} {prices[2]} {prices[3]} {prices[4]}")

print("\n  租房价格预览（元/月）:")
print(f"  {'区域':<6} {'别墅':>10} {'洋房':>10} {'高层':>10} {'老小区':>10} {'拆迁房':>10}")
print("  " + "-" * 60)
for region in REGION_NAMES:
    prices = []
    for ctype in COMMUNITY_TYPE_NAMES:
        data = get_chart_data(region, ctype, days=30, data_type="rent")
        if data["latest"]:
            prices.append(f"{data['latest']['close_price']:>10.0f}")
        else:
            prices.append(f"{'N/A':>10}")
    print(f"  {region:<6} {prices[0]} {prices[1]} {prices[2]} {prices[3]} {prices[4]}")

# 数据库统计
conn = get_connection()
cur = conn.execute("SELECT COUNT(*) FROM raw_prices")
print(f"\n  原始数据总量: {cur.fetchone()[0]} 条")
cur = conn.execute("SELECT COUNT(*) FROM ohlc_data")
print(f"  OHLC数据总量: {cur.fetchone()[0]} 条")
conn.close()

print("\n=== 数据重新生成完成 ===")
