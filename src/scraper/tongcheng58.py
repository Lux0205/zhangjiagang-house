"""
张家港房价App — 58同城爬虫
抓取58同城张家港站房价数据
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper
from src.utils.config import REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.tongcheng58")


class Tongcheng58Scraper(BaseScraper):
    """
    58同城张家港站爬虫

    URL: https://zhangjiagang.58.com/
    个人房源多，价格覆盖面广。
    """

    def __init__(self):
        super().__init__(
            source_name="58同城",
            base_url="https://zhangjiagang.58.com/"
        )

    def scrape(self) -> List[Dict]:
        """
        执行58同城数据抓取。

        返回:
            价格数据列表
        """
        all_records = []
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info("开始抓取58同城数据...")

        # 58同城张家港二手房页面
        base_urls = {
            "一环": "https://zhangjiagang.58.com/ershoufang/yangshe/",
            "二环": "https://zhangjiagang.58.com/ershoufang/yangshe/",
            "三环": "https://zhangjiagang.58.com/ershoufang/tangqiao/",
            "四环": "https://zhangjiagang.58.com/ershoufang/jinfeng/",
            "五环": "https://zhangjiagang.58.com/ershoufang/",
        }

        for region_name in REGIONS:
            try:
                url = base_urls.get(region_name, "https://zhangjiagang.58.com/ershoufang/")
                html = self.fetch_page(url)
                if html:
                    records = self._parse_prices(html, region_name, today)
                    all_records.extend(records)
                    logger.info(f"[58同城] {region_name}: 抓取到 {len(records)} 条")
            except Exception as e:
                logger.error(f"[58同城] {region_name} 抓取失败: {e}")

        logger.info(f"[58同城] 共抓取到 {len(all_records)} 条数据")
        return all_records

    def _parse_prices(self, html: str, region_name: str, today: str) -> List[Dict]:
        """
        从58同城页面HTML中解析价格数据。

        参数:
            html: 页面HTML
            region_name: 区域名称
            today: 当前日期

        返回:
            价格数据列表
        """
        records = []
        soup = BeautifulSoup(html, "lxml")

        try:
            # 58同城房源列表
            house_items = soup.select(
                ".property, .list-item, [class*='house-item'], "
                ".ershoufang-list-item, [class*='property']"
            )

            for item in house_items:
                # 房源标题/小区名
                title_elem = item.select_one(
                    ".title, [class*='title'], .prop-title a, "
                    ".house-title, [class*='name']"
                )
                community = title_elem.get_text(strip=True) if title_elem else ""

                # 单价（58同城显示总价或单价）
                price_elem = item.select_one(
                    ".unit-price, [class*='unit'], .price-per-sq, "
                    ".property-price, [class*='price']"
                )

                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price(price_text)
                    if price and 3000 <= price <= 50000:
                        records.append({
                            "date": today,
                            "region": region_name,
                            "community": community or f"{region_name}房源",
                            "price": price,
                            "unit": "元/㎡",
                            "source": self.source_name,
                        })

            # 如果列表没解析到，尝试从页面均价获取
            if not records:
                avg_elem = soup.select_one(
                    ".average-price, [class*='average'], .price-num"
                )
                if avg_elem:
                    price = self._extract_price(avg_elem.get_text(strip=True))
                    if price and 3000 <= price <= 50000:
                        records.append({
                            "date": today,
                            "region": region_name,
                            "community": f"{region_name}均价",
                            "price": price,
                            "unit": "元/㎡",
                            "source": self.source_name,
                        })

        except Exception as e:
            logger.error(f"[58同城] 解析页面失败: {e}")

        return records

    @staticmethod
    def _extract_price(text: str) -> Optional[float]:
        """
        提取价格，支持"XXXX元/㎡"和"XXXXX"两种格式。

        参数:
            text: 价格文本

        返回:
            价格数字，失败返回 None
        """
        numbers = re.findall(r'[\d.]+', text.replace(",", ""))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return None
