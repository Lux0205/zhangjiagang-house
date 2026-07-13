"""
张家港房价App — 链家网爬虫
抓取链家网张家港站区域房价数据（需要JavaScript渲染）
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.scraper.dynamic_scraper import DynamicScraper
from src.utils.config import REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.lianjia")


class LianjiaScraper(DynamicScraper):
    """
    链家网爬虫

    URL: https://su.lianjia.com/
    与贝壳同源，数据一致但页面结构略有不同。
    """

    def __init__(self):
        super().__init__(
            source_name="链家网",
            base_url="https://su.lianjia.com/"
        )

    def scrape(self) -> List[Dict]:
        """
        执行链家网数据抓取。
        """
        all_records = []
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info("开始抓取链家网数据...")

        try:
            for region_name in REGIONS:
                try:
                    url = self._get_region_url(region_name)
                    html = self.fetch_dynamic_page(url, wait_selector="[class*='price']")
                    if html:
                        records = self.parse_prices(html, region_name, today)
                        all_records.extend(records)
                        logger.info(f"[链家] {region_name}: {len(records)} 条")
                except Exception as e:
                    logger.error(f"[链家] {region_name} 抓取失败: {e}")
        finally:
            self._close_browser()

        logger.info(f"[链家] 共抓取到 {len(all_records)} 条数据")
        return all_records

    def _get_region_url(self, region_name: str) -> str:
        """
        获取区域对应的链家页面URL。
        """
        region_codes = {
            "一环": "ershoufang/yangshezhengzhong/",
            "二环": "ershoufang/yangshe/",
            "三环": "ershoufang/tangqiao/",
            "四环": "ershoufang/jinfeng/",
            "五环": "ershoufang/",
        }
        code = region_codes.get(region_name, "ershoufang/")
        return f"https://su.lianjia.com/{code}"

    def parse_prices(self, html: str, region_name: str, date: str) -> List[Dict]:
        """
        从链家页面HTML中解析价格数据。
        """
        records = []
        soup = BeautifulSoup(html, "lxml")

        try:
            # 链家均价区域
            avg_elem = soup.select_one(
                ".averagePrice, .value, [class*='average']"
            )
            if avg_elem:
                price = self._extract_number(avg_elem.get_text(strip=True))
                if price and 3000 <= price <= 50000:
                    records.append({
                        "date": date,
                        "region": region_name,
                        "community": f"{region_name}均价",
                        "price": price,
                        "unit": "元/㎡",
                        "source": self.source_name,
                    })

            # 小区列表
            house_items = soup.select(
                ".clear.xiaoquListItem, .Content__HouseItem, "
                "[class*='xiaoqu'], [class*='ListItem']"
            )

            for item in house_items:
                name_elem = item.select_one(
                    ".info .name, [class*='title'], [class*='name']"
                )
                community_name = name_elem.get_text(strip=True) if name_elem else ""

                price_elem = item.select_one(
                    ".totalPrice, .unitPrice, [class*='price'], "
                    ".averagePrice .value"
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
            logger.error(f"[链家] 解析页面失败: {e}")

        return records

    @staticmethod
    def _extract_number(text: str) -> Optional[float]:
        numbers = re.findall(r'[\d.]+', text.replace(",", ""))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return None
