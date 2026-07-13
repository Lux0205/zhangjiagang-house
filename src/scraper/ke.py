"""
张家港房价App — 贝壳找房爬虫
抓取贝壳找房张家港站区域房价数据（需要JavaScript渲染）
"""

import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.scraper.dynamic_scraper import DynamicScraper
from src.utils.config import REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.ke")


class KeScraper(DynamicScraper):
    """
    贝壳找房爬虫

    URL: https://su.ke.com/
    贝壳数据最真实，与链家同源。
    需要 JavaScript 渲染（动态加载房价信息）。
    """

    def __init__(self):
        super().__init__(
            source_name="贝壳找房",
            base_url="https://su.ke.com/"
        )
        # 张家港各区域在贝壳的页面对应（区域名称映射）
        self.region_mapping = {
            "一环": "yihuan",
            "二环": "erhuan",
            "三环": "sanyihuan",
            "四环": "sihuan",
            "五环": "zhangjiagang",
        }

    def scrape(self) -> List[Dict]:
        """
        执行贝壳找房数据抓取。
        """
        all_records = []
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info("开始抓取贝壳找房数据...")

        try:
            for region_name in REGIONS:
                try:
                    # 访问张家港贝壳首页，然后解析区域均价
                    url = self._get_region_url(region_name)
                    html = self.fetch_dynamic_page(url, wait_selector="[class*='price']")
                    if html:
                        records = self.parse_prices(html, region_name, today)
                        all_records.extend(records)
                        logger.info(f"[贝壳] {region_name}: {len(records)} 条")
                except Exception as e:
                    logger.error(f"[贝壳] {region_name} 抓取失败: {e}")
        finally:
            self._close_browser()

        logger.info(f"[贝壳] 共抓取到 {len(all_records)} 条数据")
        return all_records

    def _get_region_url(self, region_name: str) -> str:
        """
        获取区域对应的贝壳页面URL。

        参数:
            region_name: 区域名称

        返回:
            该区域的贝壳页面URL
        """
        # 张家港贝壳各区域子页面
        region_codes = {
            "一环": "ershoufang/yangshezhengzhong/",
            "二环": "ershoufang/yangshe/",
            "三环": "ershoufang/tangqiao/",
            "四环": "ershoufang/jinfeng/",
            "五环": "ershoufang/",
        }
        code = region_codes.get(region_name, "ershoufang/")
        return f"https://su.ke.com/{code}"

    def parse_prices(self, html: str, region_name: str, date: str) -> List[Dict]:
        """
        从贝壳页面HTML中解析价格数据。

        参数:
            html: 页面HTML
            region_name: 区域名称
            date: 当前日期

        返回:
            价格数据列表
        """
        records = []
        soup = BeautifulSoup(html, "lxml")

        # 贝壳页面有两种数据类型：
        # 1. 区域均价（页面顶部）
        # 2. 小区均价（列表中的小区）

        try:
            # 策略1：查找区域均价
            avg_price_elem = soup.select_one(
                ".averagePrice, [class*='average'], [class*='price'], "
                ".priceTotal, .unitPrice"
            )
            if avg_price_elem:
                price_text = avg_price_elem.get_text(strip=True)
                price = self._extract_number(price_text)
                if price and 3000 <= price <= 50000:
                    records.append({
                        "date": date,
                        "region": region_name,
                        "community": f"{region_name}均价",
                        "price": price,
                        "unit": "元/㎡",
                        "source": self.source_name,
                    })

            # 策略2：查找小区列表中的均价
            house_items = soup.select(
                ".houseCardWrapper, [class*='house'], [class*='item'], "
                ".communityCard, [class*='community']"
            )

            for item in house_items:
                # 小区名
                name_elem = item.select_one(
                    "[class*='title'], [class*='name'], .communityName a"
                )
                community_name = name_elem.get_text(strip=True) if name_elem else ""

                # 价格
                price_elem = item.select_one(
                    "[class*='price'], .unitPrice, .totalPrice, .averagePrice"
                )
                if price_elem:
                    price = self._extract_number(price_elem.get_text(strip=True))
                    if price and 3000 <= price <= 50000:
                        records.append({
                            "date": date,
                            "region": region_name,
                            "community": community_name or f"{region_name}小区",
                            "price": price,
                            "unit": "元/㎡",
                            "source": self.source_name,
                        })

        except Exception as e:
            logger.error(f"[贝壳] 解析页面失败: {e}")

        return records

    @staticmethod
    def _extract_number(text: str) -> Optional[float]:
        """
        从文本中提取数字。

        参数:
            text: 包含数字的文本

        返回:
            提取的数字，失败返回 None
        """
        numbers = re.findall(r'[\d.]+', text.replace(",", ""))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return None
