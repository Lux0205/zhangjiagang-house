"""
张家港房价App - 假数据填充模块
按小区类型（别墅/洋房/高层/老小区/拆迁房）分别生成对应的房价数据

各类型价格区间基于张家港2026年市场水平：
- 别墅：20000-40000元/㎡（一环最贵，向外递减）
- 洋房：15000-25000元/㎡
- 高层：8000-18000元/㎡
- 老小区：6000-12000元/㎡
- 拆迁房：4000-9000元/㎡
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List

from src.data.database import insert_raw_prices_batch, insert_ohlc
from src.utils.config import (
    REGION_NAMES, COMMUNITY_TYPE_NAMES, COMMUNITY_TYPES
)
from src.utils.logger import get_logger

logger = get_logger("dummy_data")

SOURCES = ["安居客", "房天下", "张家港房产网", "贝壳找房", "链家网", "58同城"]


def _get_base_price(region_name: str, community_type: str) -> float:
    """
    根据区域和类型获取基准价格。
    一环最贵，每向外一环价格递减约10-15%。
    """
    # 类型基准价（一环水平）
    type_base = {
        "别墅": 32000,
        "洋房": 20000,
        "高层": 14000,
        "老小区": 9500,
        "拆迁房": 6500,
    }

    # 区域递减系数（一环=1.0，五环=0.6）
    region_factor = {
        "一环": 1.0,
        "二环": 0.92,
        "三环": 0.80,
        "四环": 0.70,
        "五环": 0.60,
    }

    base = type_base.get(community_type, 10000)
    factor = region_factor.get(region_name, 0.8)
    return base * factor


def _get_communities(region_name: str, community_type: str) -> List[str]:
    """获取某区域某类型的参考小区列表"""
    COMMUNITIES = {
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

    region_comm = COMMUNITIES.get(region_name, {})
    return region_comm.get(community_type, [f"{region_name}{community_type}小区"])


def generate_dummy_data(days: int = 30) -> int:
    """
    生成过去N天的假数据，按小区类型分类。

    每套记录生成规则：
    - 价格 = 基准价 × 趋势因子 × 小区类型因子 + 随机波动
    - 每个区域每类型每天从小区列表中随机选3-8个出价
    - 约65%的数据源当天有数据
    """
    logger.info(f"开始生成假数据 ({days}天，按小区类型分类)...")

    total_count = 0

    for day_offset in range(days, 0, -1):
        date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")

        for region_name in REGION_NAMES:
            for ctype in COMMUNITY_TYPE_NAMES:
                base = _get_base_price(region_name, ctype)
                communities = _get_communities(region_name, ctype)

                # 趋势因子（越晚越贵，模拟通胀）
                trend = 1 + (days - day_offset) * 0.00015

                # 每天随机选3-8个小区
                num = min(len(communities), random.randint(3, 8))
                selected = random.sample(communities, num)

                records = []
                for community in selected:
                    # 每个小区每天约65%概率每个源有数据
                    for source in SOURCES:
                        if random.random() < 0.65:
                            # 源偏移（不同网站价格略有差异）
                            source_offset = random.uniform(-300, 300)
                            # 随机波动（±15%以内）
                            noise = random.uniform(-0.08, 0.08)
                            price = base * trend * (1 + noise) + source_offset
                            price = max(3000, price)

                            records.append({
                                "date": date,
                                "region": region_name,
                                "community": community,
                                "community_type": ctype,
                                "price": round(price, 2),
                                "unit": "元/㎡",
                                "source": source,
                            })

                if records:
                    insert_raw_prices_batch(records)
                    total_count += len(records)

    logger.info(f"假数据生成完成: 共 {total_count} 条")
    return total_count


def fill_ohlc_from_dummy():
    """从假数据生成OHLC聚合数据"""
    logger.info("开始按区域+类型聚合OHLC数据...")

    for day_offset in range(30, 0, -1):
        date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for region in REGION_NAMES:
            for ctype in COMMUNITY_TYPE_NAMES:
                from src.utils.aggregator import aggregate_daily_prices
                aggregate_daily_prices(date, region, ctype)

    logger.info("OHLC 聚合数据生成完成")


def ensure_data_available():
    """确保数据库中有数据，不足则填充假数据"""
    from src.data.database import get_connection

    conn = get_connection()
    cur = conn.execute("SELECT COUNT(*) as cnt FROM raw_prices")
    total = cur.fetchone()[0]
    conn.close()

    if total >= 200:
        logger.info(f"数据库已有 {total} 条数据，无需填充")
        return 0

    logger.warning(f"数据库数据不足（{total}条），填充假数据...")

    total = generate_dummy_data(30)
    fill_ohlc_from_dummy()

    logger.info(f"已填充 {total} 条假数据 + OHLC聚合数据")
    return total
