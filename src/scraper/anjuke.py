"""
张家港房价App — 安居客爬虫
抓取安居客张家港站区域房价数据
"""

from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper
from src.utils.config import REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.anjuke")


class AnjukeScraper(BaseScraper):
    """
    安居客张家港站爬虫

    URL: https://m.anjuke.com/su/trendency/zhangjiagang/
    抓取各区域二手房均价走势
    """

    def __init__(self):
        super().__init__(
            source_name="安居客",
            base_url="https://m.anjuke.com/su/trendency/zhangjiagang/"
        )
        # 安居客张家港页面目前不区分区域（所有区域共用同一页面）
        # 抓取时通过关键词匹配来区分不同区域的数据
        # TODO: 如果安居客后续提供区域子页面URL，可在此配置
        self._region_url = "https://m.anjuke.com/su/trendency/zhangjiagang/"

    def scrape(self) -> List[Dict]:
        """
        执行安居客数据抓取。

        返回:
            价格数据列表
        """
        all_records = []
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info("开始抓取安居客数据...")

        for region_name in REGIONS:
            try:
                records = self._scrape_region(region_name, today)
                all_records.extend(records)
                logger.info(f"[安居客] {region_name}: 抓取到 {len(records)} 条")
            except Exception as e:
                logger.error(f"[安居客] {region_name} 抓取失败: {e}")

        logger.info(f"[安居客] 共抓取到 {len(all_records)} 条数据")
        return all_records

    def _scrape_region(self, region_name: str, today: str) -> List[Dict]:
        """
        抓取单个区域的房价数据。
        安居客页面不区分区域，通过关键词匹配筛选。

        参数:
            region_name: 区域名称
            today: 当前日期

        返回:
            该区域的价格数据列表
        """
        html = self.fetch_page(self._region_url)
        if not html:
            return []

        records = []
        soup = BeautifulSoup(html, "lxml")

        # 解析安居客页面中的区域均价数据
        # 安居客有按区域划分的均价卡片
        try:
            # 查找区域均价列表（根据安居客页面结构）
            price_items = soup.select(".district-price-item, .area-item, [class*='price']")

            for item in price_items:
                # 提取区域名称
                area_name = item.select_one(".name, .area-name, [class*='name']")
                if not area_name:
                    continue
                area_text = area_name.get_text(strip=True)

                # 检查是否匹配当前区域关键词
                region_info = REGIONS.get(region_name, {})
                keywords = region_info.get("keywords", [])
                if not any(kw in area_text for kw in keywords):
                    continue

                # 提取价格
                price_elem = item.select_one(".price, [class*='price'] .num, .average")
                if not price_elem:
                    continue

                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price is None:
                    continue

                records.append({
                    "date": today,
                    "region": region_name,
                    "community": area_text,
                    "price": price,
                    "unit": "元/㎡",
                    "source": self.source_name,
                })

            # 如果上面没解析到，尝试备用解析策略
            if not records:
                records = self._fallback_parse(soup, region_name, today)

        except Exception as e:
            logger.error(f"[安居客] 解析 {region_name} 页面失败: {e}")

        return records

    def _fallback_parse(self, soup: BeautifulSoup, region_name: str, today: str) -> List[Dict]:
        """
        备用解析策略：尝试其他选择器模式。
        安居客的页面结构可能会更新，此方法作为兜底。
        """
        records = []
        region_info = REGIONS.get(region_name, {})
        keywords = region_info.get("keywords", [])

        # 查找所有包含价格数字的元素
        all_text = soup.get_text()

        # 尝试查找均价数据模式
        import re
        # 匹配 "均价" 后面跟数字的模式
        pattern = r'均价[：:]?\s*(\d{4,5})\s*元'
        matches = re.findall(pattern, all_text)

        for match in matches:
            price = float(match)
            records.append({
                "date": today,
                "region": region_name,
                "community": f"{region_name}均价",
                "price": price,
                "unit": "元/㎡",
                "source": self.source_name,
            })

        return records

    @staticmethod
    def _parse_price(price_text: str) -> Optional[float]:
        """
        解析价格文本，提取数字。

        参数:
            price_text: 价格文本（如 "15,426元/㎡"）

        返回:
            价格数字，解析失败返回 None
        """
        import re
        # 提取数字（去掉逗号和小数）
        numbers = re.findall(r'[\d,]+\.?\d*', price_text.replace(",", ""))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return None
