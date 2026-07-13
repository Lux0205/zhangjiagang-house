"""
张家港房价App - 多源数据聚合算法模块
将多个数据源的原始价格按【小区类型】分组聚合为 OHLC K线数据
"""

import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from src.utils.config import AGGREGATOR_CONFIG, REGION_NAMES, COMMUNITY_TYPE_NAMES
from src.data.database import (
    get_raw_prices, insert_ohlc, get_ohlc_by_region_type,
    get_latest_ohlc
)
from src.utils.logger import get_logger

logger = get_logger("aggregator")


def aggregate_daily_prices(date: str, region: str, community_type: str,
                           data_type: str = "buy") -> Optional[Dict]:
    """
    对某一区域某一天某类型的多源价格数据进行聚合。

    参数:
        date: 日期 (YYYY-MM-DD)
        region: 区域名称
        community_type: 小区类型（别墅/洋房/高层/老小区/拆迁房）
        data_type: 'buy'=买房, 'rent'=租房

    返回:
        聚合后的OHLC数据，数据不足返回 None
    """
    records = get_raw_prices(date, region, community_type, data_type=data_type)

    if not records:
        return None

    # 按数据源分组
    source_groups = _group_by_source(records)
    if len(source_groups) < 1:
        return None

    # 每个数据源分别聚合
    source_avg_prices = {}
    for src_name, group in source_groups.items():
        prices = [r["price"] for r in group]
        filtered = _remove_outliers(prices)
        if filtered:
            source_avg_prices[src_name] = {
                "avg": _safe_median(filtered),
                "min": min(filtered),
                "max": max(filtered),
                "count": len(filtered),
            }

    if not source_avg_prices:
        return None

    all_avgs = [v["avg"] for v in source_avg_prices.values()]
    all_mins = [v["min"] for v in source_avg_prices.values()]
    all_maxs = [v["max"] for v in source_avg_prices.values()]
    total_volume = sum(v["count"] for v in source_avg_prices.values())
    source_list = ",".join(source_avg_prices.keys())

    close_price = _safe_median(all_avgs)
    open_price = all_avgs[0] if len(all_avgs) == 1 else _safe_median(all_avgs[:2])
    high_price = max(all_maxs)
    low_price = min(all_mins)
    avg_price = sum(all_avgs) / len(all_avgs)

    ohlc_record = {
        "date": date,
        "region": region,
        "community_type": community_type,
        "open_price": round(open_price, 2),
        "high_price": round(high_price, 2),
        "low_price": round(low_price, 2),
        "close_price": round(close_price, 2),
        "avg_price": round(avg_price, 2),
        "volume": total_volume,
        "sources": source_list,
    }

    insert_ohlc(**ohlc_record, data_type=data_type)
    return ohlc_record


def aggregate_all_regions_types(date: str = None, data_type: str = "buy") -> Dict:
    """
    对所有区域和类型进行聚合。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    results = {}
    for region in REGION_NAMES:
        for ctype in COMMUNITY_TYPE_NAMES:
            result = aggregate_daily_prices(date, region, ctype, data_type=data_type)
            if result:
                key = f"{region}_{ctype}"
                results[key] = result

    return results


def aggregate_date_range(start_date: str = None, end_date: str = None,
                         data_type: str = "buy") -> Dict:
    """
    对一段时间内逐日聚合。

    参数:
        data_type: 'buy'=买房, 'rent'=租房
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    all_results = {}
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        results = aggregate_all_regions_types(date_str, data_type=data_type)
        all_results[date_str] = results
        current += timedelta(days=1)

    return all_results


def get_chart_data(region: str, community_type: str, days: int = 30,
                   data_type: str = "buy") -> Dict:
    """
    获取某区域某类型的K线图数据（ECharts格式）。
    默认查询最近30天。

    参数:
        data_type: 'buy'=买房, 'rent'=租房

    返回:
        ECharts K线图所需的数据字典
    """
    records = get_ohlc_by_region_type(region, community_type, days, data_type=data_type)

    if not records:
        return {
            "region": region,
            "community_type": community_type,
            "dates": [],
            "ohlcs": [],
            "volumes": [],
            "avg_prices": [],
            "latest": None,
            "change_pct": 0,
            "source_count": 0,
        }

    dates = [r["date"] for r in records]
    # ECharts K线格式: [open, close, low, high]
    ohlcs = [[r["open_price"], r["close_price"], r["low_price"], r["high_price"]]
               for r in records]
    volumes = [r["volume"] for r in records]
    avg_prices = [r["avg_price"] for r in records]

    # 计算涨跌
    if len(records) >= 2:
        latest = records[-1]
        previous = records[-2]
        change_pct = (
            (latest["close_price"] - previous["close_price"]) / previous["close_price"] * 100
            if previous["close_price"] > 0 else 0
        )
    else:
        change_pct = 0

    return {
        "region": region,
        "community_type": community_type,
        "dates": dates,
        "ohlcs": ohlcs,
        "volumes": volumes,
        "avg_prices": avg_prices,
        "latest": records[-1] if records else None,
        "change_pct": round(change_pct, 2),
        "source_count": len(records),
    }


def get_region_summary(region: str, days: int = 30, data_type: str = "buy") -> List[Dict]:
    """
    获取某区域所有小区类型的汇总统计（用于底部信息展示）。

    参数:
        data_type: 'buy'=买房, 'rent'=租房

    返回:
        各类型汇总列表，例如:
        [
            {"type": "别墅", "avg_price": 28500, "change_pct": 1.2, "volume": 50},
            {"type": "高层", "avg_price": 13200, "change_pct": -0.5, "volume": 200},
            ...
        ]
    """
    summary = []
    for ctype in COMMUNITY_TYPE_NAMES:
        data = get_chart_data(region, ctype, days, data_type=data_type)
        if data["latest"]:
            summary.append({
                "type": ctype,
                "avg_price": data["latest"]["close_price"],
                "change_pct": data["change_pct"],
                "volume": data["latest"]["volume"],
            })
    return summary


# ===== 内部工具 =====

def _group_by_source(records: List[Dict]) -> Dict[str, List[Dict]]:
    groups = {}
    for r in records:
        src = r.get("source", "未知")
        if src not in groups:
            groups[src] = []
        groups[src].append(r)
    return groups


def _remove_outliers(prices: List[float]) -> List[float]:
    if len(prices) <= 2:
        return prices
    threshold = AGGREGATOR_CONFIG["outlier_threshold"]
    avg = sum(prices) / len(prices)
    lower = avg * (1 - threshold)
    upper = avg * (1 + threshold)
    filtered = [p for p in prices if lower <= p <= upper]
    return filtered if filtered else prices


def _safe_median(values: List[float]) -> float:
    if not values:
        return 0.0
    try:
        return statistics.median(values)
    except statistics.StatisticsError:
        return 0.0
