"""
张家港房价App — 房天下爬虫
抓取房天下张家港站区域房价数据
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper
from src.utils.config import REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.fang")


class FangScraper(BaseScraper):
    """
    房天下张家港站爬虫

    URL: http://fangjia.fang.com/zjg/
    抓取张家港各区域二手房均价
    """

    def __init__(self):
        super().__init__(
            source_name="房天下",
            base_url="http://fangjia.fang.com/zjg/"
        )

    def scrape(self) -> List[Dict]:
        """
        执行房天下数据抓取。

        返回:
            价格数据列表
        """
        all_records = []
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info("开始抓取房天下数据...")

        # 抓取主页面获取各区域均价
        html = self.fetch_page(self.base_url)
        if not html:
            return all_records

        soup = BeautifulSoup(html, "lxml")

        for region_name in REGIONS:
            try:
                records = self._extract_prices(soup, region_name, today)
                all_records.extend(records)
                logger.info(f"[房天下] {region_name}: 抓取到 {len(records)} 条")
            except Exception as e:
                logger.error(f"[房天下] {region_name} 抓取失败: {e}")

        logger.info(f"[房天下] 共抓取到 {len(all_records)} 条数据")
        return all_records

    def _extract_prices(self, soup: BeautifulSoup, region_name: str, today: str) -> List[Dict]:
        """
        从页面中提取指定区域的房价数据。

        参数:
            soup: BeautifulSoup解析对象
            region_name: 区域名称
            today: 当前日期

        返回:
            该区域的价格数据列表
        """
        records = []
        region_info = REGIONS.get(region_name, {})
        keywords = region_info.get("keywords", [])
        communities = region_info.get("communities", [])

        # 策略1：查找区域均价数据
        # 房天下页面有各区域的均价卡片
        price_sections = soup.select(
            ".district-price, .area-price, [class*='fangjia'], "
            ".price-list, .region-list, [class*='region']"
        )

        for section in price_sections:
            text = section.get_text(strip=True)

            # 检查是否匹配当前区域
            if not any(kw in text for kw in keywords):
                continue

            # 提取价格数字
            prices = re.findall(r'(\d{4,5})\s*元?', text)
            for price_str in prices:
                price = float(price_str)
                # 合理范围检查
                if 3000 <= price <= 50000:
                    records.append({
                        "date": today,
                        "region": region_name,
                        "community": f"{region_name}区域均价",
                        "price": price,
                        "unit": "元/㎡",
                        "source": self.source_name,
                    })

        # 策略2：用小区名匹配
        if not records and communities:
            for community in communities:
                # 在页面中查找小区名对应的区域
                elements = soup.find_all(string=re.compile(re.escape(community)))
                for elem in elements:
                    parent = elem.parent
                    if parent:
                        text = parent.get_text()
                        prices = re.findall(r'(\d{4,5})\s*元?', text)
                        for price_str in prices:
                            price = float(price_str)
                            if 3000 <= price <= 50000:
                                records.append({
                                    "date": today,
                                    "region": region_name,
                                    "community": community,
                                    "price": price,
                                    "unit": "元/㎡",
                                    "source": self.source_name,
                                })

        return records
