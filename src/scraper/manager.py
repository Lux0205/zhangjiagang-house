"""
张家港房价App — 爬虫管理器
统一调度所有数据源的爬虫，收集数据并持久化"""

from datetime import datetime
from typing import List, Dict, Optional

# 导入所有爬虫
from src.scraper.anjuke import AnjukeScraper
from src.scraper.fang import FangScraper
from src.scraper.zjgzf import ZjgzfScraper
from src.scraper.ke import KeScraper
from src.scraper.lianjia import LianjiaScraper
from src.scraper.tongcheng58 import Tongcheng58Scraper
from src.utils.config import SCRAPER_SOURCES, REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.manager")

# 爬虫注册表
SCRAPER_REGISTRY = {
    "anjuke": AnjukeScraper,
    "fang": FangScraper,
    "zjgzf": ZjgzfScraper,
    "ke": KeScraper,
    "lianjia": LianjiaScraper,
    "tongcheng58": Tongcheng58Scraper,
}


class ScraperManager:
    """
    爬虫管理器，统一启动和管理所有数据源爬虫。
    """

    def __init__(self):
        """
        初始化管理器。
        """
        self.scrapers: Dict[str, object] = {}
        self.results: Dict[str, List[Dict]] = {}
        self.errors: Dict[str, str] = {}
        self._init_scrapers()

    def _init_scrapers(self):
        """创建所有已启用的爬虫实例。"""
        for key, source_config in SCRAPER_SOURCES.items():
            if not source_config.get("enabled", False):
                continue

            scraper_class = SCRAPER_REGISTRY.get(key)
            if scraper_class:
                self.scrapers[key] = scraper_class()
                logger.info(f"已注册爬虫: {source_config['name']}")
            else:
                logger.warning(f"未知爬虫类型: {key}")

    def run_all(self, data_type: str = "buy") -> Dict[str, List[Dict]]:
        """
        运行所有爬虫，收集数据。

        参数:
            data_type: 'buy'=买房, 'rent'=租房

        返回:
            所有爬虫的结果字典 {数据源名: 数据列表}
        """
        self.results = {}
        self.errors = {}

        type_label = "租房" if data_type == "rent" else "买房"
        logger.info(f"开始全量抓取 ({type_label})，共 {len(self.scrapers)} 个数据源...")

        total_start = datetime.now()

        for key, scraper in self.scrapers.items():
            try:
                logger.info(f"开始抓取: {scraper.source_name}")
                records = scraper.scrape()

                # 过滤有效记录，并打上 data_type 标签
                valid_records = []
                for r in records:
                    if scraper.validate_record(r):
                        r["data_type"] = data_type
                        valid_records.append(r)
                self.results[key] = valid_records

                logger.info(f"[完成] {scraper.source_name}: {len(valid_records)}/{len(records)} 条有效")

            except Exception as e:
                self.errors[key] = str(e)
                logger.error(f"[失败] {scraper.source_name}: {e}")

        elapsed = (datetime.now() - total_start).total_seconds()
        total_count = sum(len(v) for v in self.results.values())
        logger.info(f"全量抓取完成 ({type_label}): {total_count} 条数据，耗时 {elapsed:.1f} 秒，{len(self.errors)} 个源失败")

        return self.results

    def run_single(self, source_key: str) -> List[Dict]:
        """
        运行单个爬虫。

        参数:
            source_key: 数据源标识（如 'anjuke'）

        返回:
            该爬虫的结果列表
        """
        scraper = self.scrapers.get(source_key)
        if not scraper:
            logger.error(f"未知的数据源: {source_key}")
            return []

        try:
            records = scraper.scrape()
            valid_records = [r for r in records if scraper.validate_record(r)]
            logger.info(f"[{source_key}] 抓取完成: {len(valid_records)} 条")
            return valid_records
        except Exception as e:
            logger.error(f"[{source_key}] 抓取失败: {e}")
            return []

    def get_all_records(self) -> List[Dict]:
        """
        获取所有爬虫的扁平化数据列表。

        Returns:
            所有数据合并后的列表
        """
        all_records = []
        for records in self.results.values():
            all_records.extend(records)
        return all_records

    def get_summary(self) -> Dict:
        """获取抓取摘要"""
        return {
            "total_sources": len(self.scrapers),
            "success_sources": len(self.results),
            "failed_sources": len(self.errors),
            "total_records": sum(len(v) for v in self.results.values()),
            "errors": {k: v for k, v in self.errors.items()},
        }
