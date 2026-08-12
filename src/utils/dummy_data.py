"""
张家港房价App - 假数据填充模块
支持两种数据类型：
  - 买房价格（元/㎡）
  - 租房价格（元/月）
按小区类型（别墅/洋房/高层/老小区/拆迁房）分别生成对应数据

基准价基于房天下（fangjia.fang.com）2026年8月张家港真实数据推算：
【买房】别墅27000 洋房20000 高层17000 老小区12500 拆迁房9500（元/㎡，一环水平）
【租房】别墅4000 洋房2500 高层1800 老小区1000 拆迁房700（元/月，一环水平）
区域因子：一环=1.0 二环=0.91 三环=0.69 四环=0.58 五环=0.54
"""

import random
import functools
from datetime import datetime, timedelta
from typing import Dict, List

from src.data.database import insert_raw_prices_batch, insert_ohlc
from src.utils.config import (
    REGION_NAMES, COMMUNITY_TYPE_NAMES, COMMUNITY_TYPES,
    BUY_BASE_PRICES, RENT_BASE_PRICES, DATA_TYPE_UNIT,
    DATA_TYPES, DATA_TYPE_NAMES, REGION_FACTORS
)
from src.utils.logger import get_logger

logger = get_logger("dummy_data")

SOURCES = ["安居客", "房天下", "张家港房产网", "贝壳找房", "链家网", "58同城"]


@functools.lru_cache(maxsize=1)
def _get_communities_cached() -> dict:
    """缓存版小区数据（只构建一次，后续调用返回缓存）"""
    return {
        "一环": {
            "别墅": ["甲江南别墅", "蓝波金典别墅", "置地甲江南", "中港别墅"],
            "洋房": ["中港花苑", "蓝波金典", "王府名居", "江南明珠"],
            "高层": ["置地甲江南高层", "胜利新村", "沙洲新村", "杨舍老街"],
            "老小区": ["胜利新村老小区", "城北新村", "沙洲新村", "杨舍老街老楼"],
            "拆迁房": ["杨舍安置房", "沙洲安居房", "城中新村"],
        },
        "二环": {
            "别墅": ["建发御珑湾别墅", "世茂九溪墅", "花园浜别墅", "亨通别墅"],
            "洋房": ["建发御珑湾", "西湖苑", "观唐", "湖滨国际"],
            "高层": ["花园浜", "亨通花园", "西湖苑高层", "缇香郡"],
            "老小区": ["花园浜老小区", "亨通老村", "西湖苑老楼", "城北大院"],
            "拆迁房": ["城东安置小区", "花园浜安居房", "亨通安置区"],
        },
        "三环": {
            "别墅": ["塘桥别墅", "金港别墅", "后塍别墅", "德积花园"],
            "洋房": ["塘桥洋房", "金港花园", "金科廊桥", "保菱花园"],
            "高层": ["塘桥维达", "金港中兴", "后塍中心", "德积镇中"],
            "老小区": ["塘桥老镇区", "金港老小区", "后塍老街", "德积老村"],
            "拆迁房": ["塘桥安置房", "金港拆迁安置", "后塍安居工程"],
        },
        "四环": {
            "别墅": ["锦丰别墅", "凤凰别墅", "乐余花园", "南丰别墅"],
            "洋房": ["锦丰洋房", "凤凰花园", "乐余洋房", "南丰名苑"],
            "高层": ["锦丰青年路", "凤凰镇区", "乐余中心", "南丰镇中"],
            "老小区": ["锦丰老镇区", "凤凰老街", "乐余老街", "南丰老镇"],
            "拆迁房": ["锦丰安置房", "凤凰安居", "乐余拆迁房"],
        },
        "五环": {
            "别墅": ["全市别墅参考", "远郊别墅"],
            "洋房": ["全市洋房参考", "镇域花园"],
            "高层": ["全市均价参考", "杨舍均价参考"],
            "老小区": ["全市老小区参考", "乡镇老街"],
            "拆迁房": ["全市安置房参考", "农村安居"],
        },
    }


def _generate_records_for_day(date: str, region_name: str, ctype: str,
                              base: float, trend: float, data_type: str,
                              unit: str, communities: list) -> list:
    """
    为某一天某区域某类型生成假数据记录。
    被 generate_dummy_data 和 _generate_for_missing_combinations 共用。

    参数:
        date: 日期字符串
        region_name: 区域名称
        ctype: 小区类型
        base: 基准价格
        trend: 趋势因子
        data_type: 'buy'=买房, 'rent'=租房
        unit: 价格单位
        communities: 小区列表

    返回:
        记录字典列表
    """
    num = min(len(communities), random.randint(3, 8))
    selected = random.sample(communities, num)

    records = []
    for community in selected:
        # 每个小区每天约65%概率每个源有数据
        for source in SOURCES:
            if random.random() < 0.65:
                # 源偏移：不同网站价格略有差异（基准价的 ±3%）
                source_offset = base * random.uniform(-0.03, 0.03)
                # 随机波动（±5%以内）
                noise = random.uniform(-0.05, 0.05)
                price = base * trend * (1 + noise) + source_offset
                # 租房最低100元/月，买房最低3000元/㎡
                price = max(100 if data_type == "rent" else 3000, price)

                records.append({
                    "date": date,
                    "region": region_name,
                    "community": community,
                    "community_type": ctype,
                    "data_type": data_type,
                    "price": round(price, 2),
                    "unit": unit,
                    "source": source,
                })
    return records


def _get_base_price(region_name: str, community_type: str, data_type: str = "buy") -> float:
    """
    根据区域、类型和数据类型获取基准价格。
    一环最贵，每向外一环价格递减（基于房天下真实数据计算的区域因子）。

    参数:
        data_type: 'buy'=买房(元/㎡), 'rent'=租房(元/月)
    """
    # 根据数据类型选择基准价表
    if data_type == "rent":
        type_base = RENT_BASE_PRICES
    else:
        type_base = BUY_BASE_PRICES

    # 区域因子（基于房天下2026年8月真实数据计算）
    # 一环=1.0, 二环=0.91, 三环=0.69, 四环=0.58, 五环=0.54
    base = type_base.get(community_type, 10000)
    factor = REGION_FACTORS.get(region_name, 0.54)
    return base * factor


def _get_communities(region_name: str, community_type: str) -> List[str]:
    """获取某区域某类型的参考小区列表（使用缓存）"""
    communities_data = _get_communities_cached()
    region_comm = communities_data.get(region_name, {})
    return region_comm.get(community_type, [f"{region_name}{community_type}小区"])


def generate_dummy_data(days: int = 30, data_type: str = "buy") -> int:
    """
    生成过去N天的假数据，按小区类型分类。

    参数:
        days: 生成多少天的数据
        data_type: 'buy'=买房(元/㎡), 'rent'=租房(元/月)

    每套记录生成规则：
    - 价格 = 基准价 × 趋势因子 + 随机波动
    - 每个区域每类型每天从小区列表中随机选3-8个出价
    - 约65%的数据源当天有数据
    """
    type_label = DATA_TYPES.get(data_type, "买房价格")
    logger.info(f"开始生成假数据 ({days}天, {type_label}, data_type={data_type})...")

    total_count = 0
    unit = DATA_TYPE_UNIT.get(data_type, "元/㎡")

    for day_offset in range(days, 0, -1):
        date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")

        for region_name in REGION_NAMES:
            for ctype in COMMUNITY_TYPE_NAMES:
                base = _get_base_price(region_name, ctype, data_type)
                communities = _get_communities(region_name, ctype)

                # 趋势因子（越晚越贵，模拟通胀）
                trend = 1 + (days - day_offset) * 0.00015

                records = _generate_records_for_day(
                    date, region_name, ctype, base, trend, data_type, unit, communities
                )

                if records:
                    insert_raw_prices_batch(records)
                    total_count += len(records)

    logger.info(f"假数据生成完成 ({type_label}): 共 {total_count} 条")
    return total_count


def fill_ohlc_from_dummy(data_type: str = "buy"):
    """
    从假数据生成OHLC聚合数据（使用批量聚合，速度提升数倍）。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    type_label = DATA_TYPES.get(data_type, "买房价格")
    logger.info(f"开始按区域+类型聚合OHLC数据 ({type_label})...")

    # 生成日期列表，一次性批量聚合
    dates = [(datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
            for d in range(30, 0, -1)]
    from src.utils.aggregator import aggregate_batch
    count = aggregate_batch(dates, data_type=data_type)

    logger.info(f"OHLC 聚合数据生成完成 ({type_label}): {count} 条")


def _count_ohlc_completeness(conn, data_type: str) -> tuple:
    """
    检查OHLC数据完整性。
    返回 (已有组合数, 缺失组合列表)
    """
    # 期望的组合数：5区域 × 5类型 = 25
    expected = len(REGION_NAMES) * len(COMMUNITY_TYPE_NAMES)
    cur = conn.execute(
        "SELECT DISTINCT region, community_type FROM ohlc_data WHERE data_type=?",
        (data_type,)
    )
    existing = {(row[0], row[1]) for row in cur.fetchall()}
    missing = []
    for r in REGION_NAMES:
        for t in COMMUNITY_TYPE_NAMES:
            if (r, t) not in existing:
                missing.append((r, t))
    return len(existing), missing


def ensure_data_available():
    """
    确保数据库中有数据，不足则填充假数据。
    同时填充买房和租房两类数据。

    修复：同时检查 raw_prices 和 ohlc_data 的完整性，
    如果OHLC缺失则从原始数据重新聚合，原始数据也不足则生成假数据。
    """
    from src.data.database import get_connection
    from src.utils.aggregator import aggregate_daily_prices

    conn = get_connection()

    # 统计各类数据的现有数量
    type_counts = {}
    for dt in DATA_TYPE_NAMES:
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM raw_prices WHERE data_type=?", (dt,)
        )
        type_counts[dt] = cur.fetchone()[0]

    conn.close()

    total_added = 0

    for dt in DATA_TYPE_NAMES:
        type_label = DATA_TYPES[dt]
        raw_count = type_counts[dt]

        # 检查OHLC完整性
        conn = get_connection()
        ohlc_count, ohlc_missing = _count_ohlc_completeness(conn, dt)
        conn.close()

        # 情况1：原始数据不足 → 生成假数据并聚合
        if raw_count < 200:
            logger.warning(f"{type_label}原始数据不足（{raw_count}条），填充假数据...")
            total_added += generate_dummy_data(30, data_type=dt)
            fill_ohlc_from_dummy(data_type=dt)
            continue

        # 情况2：原始数据够但OHLC不完整 → 从原始数据重新聚合
        if ohlc_missing:
            logger.warning(f"{type_label}OHLC缺失 {len(ohlc_missing)} 个组合，重新聚合...")
            # 找出有原始数据的日期
            conn = get_connection()
            cur = conn.execute(
                "SELECT DISTINCT date FROM raw_prices WHERE data_type=?",
                (dt,)
            )
            dates = [row[0] for row in cur.fetchall()]
            conn.close()

            for date in dates:
                for region, ctype in ohlc_missing:
                    aggregate_daily_prices(date, region, ctype, data_type=dt)

            # 检查是否还有缺失（可能某些组合完全没有原始数据）
            conn = get_connection()
            _, still_missing = _count_ohlc_completeness(conn, dt)
            conn.close()

            if still_missing:
                # 为完全缺失的组合生成30天假数据
                logger.warning(f"{type_label}仍有 {len(still_missing)} 个组合无原始数据，生成假数据...")
                _generate_for_missing_combinations(dt, still_missing)
                logger.info(f"{type_label}缺失组合假数据生成完成")

        logger.info(f"{type_label}: 原始数据 {raw_count} 条, OHLC {ohlc_count} 个组合")

    logger.info(f"数据填充完成，共新增 {total_added} 条")
    return total_added


def _generate_for_missing_combinations(data_type: str, missing: list):
    """
    为缺失的组合生成30天假数据并聚合OHLC。
    复用 _generate_records_for_day 生成记录，再逐日聚合。
    """
    from src.utils.aggregator import aggregate_daily_prices
    from datetime import datetime, timedelta

    unit = DATA_TYPE_UNIT.get(data_type, "元/㎡")

    for day_offset in range(30, 0, -1):
        date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for region, ctype in missing:
            base = _get_base_price(region, ctype, data_type)
            communities = _get_communities(region, ctype)
            trend = 1 + (30 - day_offset) * 0.00015

            records = _generate_records_for_day(
                date, region, ctype, base, trend, data_type, unit, communities
            )

            if records:
                insert_raw_prices_batch(records)
                aggregate_daily_prices(date, region, ctype, data_type=data_type)
