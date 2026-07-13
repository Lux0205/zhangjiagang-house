"""
张家港房价App - 假数据填充模块
支持两种数据类型：
  - 买房价格（元/㎡）
  - 租房价格（元/月）
按小区类型（别墅/洋房/高层/老小区/拆迁房）分别生成对应数据

各类型价格基于张家港2026年市场水平：
【买房】别墅32000 洋房20000 高层14000 老小区9500 拆迁房6500（元/㎡）
【租房】别墅2500 洋房1800 高层1200 老小区800 拆迁房500（元/月）
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List

from src.data.database import insert_raw_prices_batch, insert_ohlc
from src.utils.config import (
    REGION_NAMES, COMMUNITY_TYPE_NAMES, COMMUNITY_TYPES,
    BUY_BASE_PRICES, RENT_BASE_PRICES, DATA_TYPE_UNIT
)
from src.utils.logger import get_logger

logger = get_logger("dummy_data")

SOURCES = ["安居客", "房天下", "张家港房产网", "贝壳找房", "链家网", "58同城"]


def _get_base_price(region_name: str, community_type: str, data_type: str = "buy") -> float:
    """
    根据区域、类型和数据类型获取基准价格。
    一环最贵，每向外一环价格递减约10-15%。

    参数:
        data_type: 'buy'=买房(元/㎡), 'rent'=租房(元/月)
    """
    # 根据数据类型选择基准价表
    if data_type == "rent":
        type_base = RENT_BASE_PRICES
    else:
        type_base = BUY_BASE_PRICES

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
    type_label = "租房" if data_type == "rent" else "买房"
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

                if records:
                    insert_raw_prices_batch(records)
                    total_count += len(records)

    logger.info(f"假数据生成完成 ({type_label}): 共 {total_count} 条")
    return total_count


def fill_ohlc_from_dummy(data_type: str = "buy"):
    """
    从假数据生成OHLC聚合数据。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    type_label = "租房" if data_type == "rent" else "买房"
    logger.info(f"开始按区域+类型聚合OHLC数据 ({type_label})...")

    for day_offset in range(30, 0, -1):
        date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for region in REGION_NAMES:
            for ctype in COMMUNITY_TYPE_NAMES:
                from src.utils.aggregator import aggregate_daily_prices
                aggregate_daily_prices(date, region, ctype, data_type=data_type)

    logger.info(f"OHLC 聚合数据生成完成 ({type_label})")


def ensure_data_available():
    """
    确保数据库中有数据，不足则填充假数据。
    同时填充买房和租房两类数据。
    """
    from src.data.database import get_connection

    conn = get_connection()

    # 检查买房数据
    cur = conn.execute("SELECT COUNT(*) as cnt FROM raw_prices WHERE data_type='buy'")
    buy_total = cur.fetchone()[0]

    # 检查租房数据
    cur = conn.execute("SELECT COUNT(*) as cnt FROM raw_prices WHERE data_type='rent'")
    rent_total = cur.fetchone()[0]

    conn.close()

    total_added = 0

    # 填充买房假数据
    if buy_total < 200:
        logger.warning(f"买房数据不足（{buy_total}条），填充假数据...")
        total_added += generate_dummy_data(30, data_type="buy")
        fill_ohlc_from_dummy(data_type="buy")
    else:
        logger.info(f"买房数据已有 {buy_total} 条，无需填充")

    # 填充租房假数据
    if rent_total < 200:
        logger.warning(f"租房数据不足（{rent_total}条），填充假数据...")
        total_added += generate_dummy_data(30, data_type="rent")
        fill_ohlc_from_dummy(data_type="rent")
    else:
        logger.info(f"租房数据已有 {rent_total} 条，无需填充")

    logger.info(f"数据填充完成，共新增 {total_added} 条")
    return total_added
