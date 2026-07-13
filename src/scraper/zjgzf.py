"""
张家港房产网爬虫
抓取张家港房产网本地房价数据
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper
from src.utils.config import REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.zjgzf")


class ZjgzfScraper(BaseScraper):
    """
    张家港房产网爬虫

    URL: http://www.zjgzf.cn/
    本地信息较精准，覆盖张家港各镇区
    """

    def __init__(self):
        super().__init__(
            source_name="张家港房产网",
            base_url="http://www.zjgzf.cn/"
        )

    def scrape(self) -> List[Dict]:
        """
        执行张家港房产网数据抓取。

        返回:
            价格数据列表
        """
        all_records = []
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info("开始抓取张家港房产网数据...")

        html = self.fetch_page(self.base_url)
        if not html:
            return all_records

        soup = BeautifulSoup(html, "lxml")

        for region_name in REGIONS:
            try:
                records = self._extract_prices(soup, region_name, today)
                all_records.extend(records)
                logger.info(f"[张家港房产网] {region_name}: 抓取到 {len(records)} 条")
            except Exception as e:
                logger.error(f"[张家港房产网] {region_name} 抓取失败: {e}")

        logger.info(f"[张家港房产网] 共抓取到 {len(all_records)} 条数据")
        return all_records

    def _extract_prices(self, soup: BeautifulSoup, region_name: str, today: str) -> List[Dict]:
        """
        从页面中提取指定区域的房价数据。
        """
        records = []
        region_info = REGIONS.get(region_name, {})
        keywords = region_info.get("keywords", [])

        # 提取页面中所有文本块
        text_blocks = soup.find_all(["div", "li", "td", "span", "a", "p"])

        for block in text_blocks:
            text = block.get_text(strip=True)
            if not text or len(text) > 200:
                continue

            # 检查是否匹配当前区域关键词
            if not any(kw in text for kw in keywords):
                continue

            # 提取价格
            prices = re.findall(r'(\d{4,5})\s*(?:元/㎡|元|元/平)?', text)
            for price_str in prices:
                price = float(price_str)
                if 3000 <= price <= 50000:
                    records.append({
                        "date": today,
                        "region": region_name,
                        "community": text[:50],  # 截取前50字符作为小区名
                        "price": price,
                        "unit": "元/㎡",
                        "source": self.source_name,
                    })

        return records
