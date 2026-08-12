"""
张家港房价App — 房天下爬虫
抓取房天下张家港站各区域房价数据（静态页面，可稳定抓取）

数据来源: http://fangjia.fang.com/zjg/
可获取数据:
  - 全市二手房/新房均价
  - 各区域二手房均价（市中心、城东、城西、城南、城北、金港、锦丰、塘桥、凤凰、大新、乐余、南丰等）
  - 热门小区排行榜（小区名 + 参考价）
"""

import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper
from src.utils.config import REGIONS
from src.utils.logger import get_logger

logger = get_logger("scraper.fang")


# 房天下张家港各区域页面代码
# 数据来源: http://fangjia.fang.com/zjg/ 页内链接
AREA_CODES = {
    "市中心": "a017470-b030568",
    "城东": "a017470-b022634",
    "城西": "a017470-b022633",
    "城南": "a017470-b022635",
    "城北": "a017470-b022636",
    "金港": "a017470-b019124",
    "锦丰": "a017470-b019127",
    "塘桥": "a017470-b019130",
    "凤凰": "a017470-b019133",
    "大新": "a017470-b019135",
    "乐余": "a017470-b019136",
    "南丰": "a017470-b019137",
    "常阴沙": "a017470-b019138",
}

# 房天下区域 → 五环映射
# 房天下的区域划分与软件的五环划分不完全对应，按地理位置映射
AREA_TO_RING = {
    "市中心": "一环",
    "城东": "二环",
    "城西": "二环",
    "城南": "二环",
    "城北": "二环",
    "塘桥": "三环",
    "金港": "三环",
    "锦丰": "四环",
    "凤凰": "四环",
    "乐余": "四环",
    "南丰": "四环",
    "大新": "四环",
    "常阴沙": "四环",
}


class FangScraper(BaseScraper):
    """
    房天下张家港站爬虫

    URL: http://fangjia.fang.com/zjg/
    抓取各区域二手房均价和热门小区排行榜。
    房天下页面是静态HTML，不依赖JavaScript渲染，可稳定抓取。
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
            价格数据列表，每条记录包含 date, region, community, price, unit, source, data_type
        """
        all_records = []
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info("开始抓取房天下数据...")

        # 1. 抓取全市均价
        citywide = self._get_citywide_price()
        if citywide:
            if citywide.get("ershou"):
                all_records.append({
                    "date": today,
                    "region": "五环",
                    "community": "全市二手房均价",
                    "price": citywide["ershou"],
                    "unit": "元/㎡",
                    "source": self.source_name,
                    "data_type": "buy",
                })
            if citywide.get("xin"):
                all_records.append({
                    "date": today,
                    "region": "五环",
                    "community": "全市新房均价",
                    "price": citywide["xin"],
                    "unit": "元/㎡",
                    "source": self.source_name,
                    "data_type": "buy",
                })
            logger.info(f"[房天下] 全市二手房均价: {citywide.get('ershou')} 元/平, "
                        f"新房均价: {citywide.get('xin')} 元/平")

        # 2. 抓取各区域均价
        for area_name, code in AREA_CODES.items():
            try:
                area_prices = self._get_area_price(area_name, code)
                ring = AREA_TO_RING.get(area_name, "五环")

                if area_prices.get("ershou"):
                    all_records.append({
                        "date": today,
                        "region": ring,
                        "community": f"{area_name}二手房均价",
                        "price": area_prices["ershou"],
                        "unit": "元/㎡",
                        "source": self.source_name,
                        "data_type": "buy",
                    })

                if area_prices.get("xin"):
                    all_records.append({
                        "date": today,
                        "region": ring,
                        "community": f"{area_name}新房均价",
                        "price": area_prices["xin"],
                        "unit": "元/㎡",
                        "source": self.source_name,
                        "data_type": "buy",
                    })

                logger.info(f"[房天下] {area_name}({ring}): "
                            f"二手房 {area_prices.get('ershou')} 元/平, "
                            f"新房 {area_prices.get('xin')} 元/平")

                # 限流：每个区域请求间隔 ≥ 5秒
                time.sleep(self.config["request_delay"])

            except Exception as e:
                logger.error(f"[房天下] {area_name} 抓取失败: {e}")

        # 3. 抓取热门小区排行榜
        ranking = self._get_community_ranking()
        for item in ranking:
            # 热门小区大多位于市中心（一环）
            all_records.append({
                "date": today,
                "region": "一环",
                "community": item["community"],
                "price": item["price"],
                "unit": "元/㎡",
                "source": self.source_name,
                "data_type": "buy",
            })
        logger.info(f"[房天下] 热门小区排行榜: {len(ranking)} 个")

        # 4. 补充缺失区域：市中心和常阴沙在房天下没有独立数据
        # 用已有数据推算：一环 ≈ 二环均价 / 0.91，常阴沙 ≈ 南丰价格
        ring_prices = {}
        for r in all_records:
            if r["data_type"] == "buy" and "均价" in r.get("community", ""):
                ring = r["region"]
                if ring not in ring_prices:
                    ring_prices[ring] = []
                ring_prices[ring].append(r["price"])

        # 如果一环没有区域均价（只有小区数据），用二环均价推算
        if "一环" not in ring_prices and "二环" in ring_prices:
            avg_erhou = sum(ring_prices["二环"]) / len(ring_prices["二环"])
            # 一环 ≈ 二环 / 0.91（区域因子比）
            estimated_yihuan = avg_erhou / 0.91
            all_records.append({
                "date": today,
                "region": "一环",
                "community": "市中心二手房均价(推算)",
                "price": round(estimated_yihuan, 2),
                "unit": "元/㎡",
                "source": self.source_name,
                "data_type": "buy",
            })
            logger.info(f"[房天下] 一环均价推算: {round(estimated_yihuan, 2)} 元/平（基于二环均价 {round(avg_erhou, 2)}）")

        logger.info(f"[房天下] 共抓取到 {len(all_records)} 条数据")
        return all_records

    def _get_citywide_price(self) -> Optional[Dict]:
        """
        获取全市均价。

        返回:
            {"ershou": 二手房均价, "xin": 新房均价}，无数据返回 None
        """
        html = self.fetch_page(self.base_url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        result = {}

        # 房天下全市均价HTML结构:
        # <li class="title_list"> 八月二手房参考均价...</li>
        # <li class="title_num"><span> 9153</span>元/平</li>
        for ul in soup.select("ul"):
            text = ul.get_text(strip=True)
            if "二手房" in text and "元/平" in text:
                match = re.search(r"([\d,]+)\s*元/平", text)
                if match:
                    result["ershou"] = float(match.group(1).replace(",", ""))
            elif "新房" in text and "元/平" in text:
                match = re.search(r"([\d,]+)\s*元/平", text)
                if match:
                    result["xin"] = float(match.group(1).replace(",", ""))

        return result if result else None

    def _get_area_price(self, area_name: str, code: str) -> Dict:
        """
        获取单个区域的均价。

        参数:
            area_name: 区域名称
            code: 房天下区域代码

        返回:
            {"ershou": 二手房均价, "xin": 新房均价}
        """
        url = f"http://fangjia.fang.com/zjg/{code}/"
        html = self.fetch_page(url)
        if not html:
            return {}

        soup = BeautifulSoup(html, "lxml")
        result = {}

        # 方式1: 查找 <em> 标签中的数字（区域页面结构）
        # <em>9349</em>元/平
        for em in soup.select("em"):
            text = em.get_text(strip=True)
            if re.match(r"^[\d,]+$", text):
                price = float(text.replace(",", ""))
                if 3000 <= price <= 50000:
                    if "ershou" not in result:
                        result["ershou"] = price
                    elif "xin" not in result:
                        result["xin"] = price
                        break

        # 方式2: 查找包含"八月参考均价"的文本
        if not result:
            for elem in soup.find_all(string=re.compile(r"八月参考均价")):
                parent = elem.parent
                if parent:
                    granpa = parent.parent
                    if granpa:
                        nums = re.findall(r"([\d,]+)\s*元/平", granpa.get_text())
                        if nums:
                            result["ershou"] = float(nums[0].replace(",", ""))

        return result

    def _get_community_ranking(self) -> List[Dict]:
        """
        获取热门小区排行榜。

        返回:
            排行榜列表，每条包含 rank, community, listing_count, price
        """
        html = self.fetch_page(self.base_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        ranking = []

        # 排行榜HTML结构:
        # <dl class="clearfix">
        #   <dt class="red-num">1</dt>
        #   <dd>
        #     <p class="blod"><a>世茂九溪墅</a><span class="pm-price">挂牌34套</span></p>
        #     <p class="f14"><span>参考价</span><span class="pm-rate"> 18745元/平米</span></p>
        #   </dd>
        # </dl>
        for dl in soup.select("dl.clearfix"):
            dt = dl.select_one("dt")
            dd = dl.select_one("dd")
            if not dt or not dd:
                continue

            rank_text = dt.get_text(strip=True)
            if not rank_text.isdigit():
                continue

            # 小区名
            name_elem = dd.select_one("a")
            community_name = name_elem.get_text(strip=True) if name_elem else ""

            # 挂牌数
            listing_elem = dd.select_one(".pm-price")
            listing_text = listing_elem.get_text(strip=True) if listing_elem else ""
            listing_match = re.search(r"(\d+)", listing_text)
            listing_count = int(listing_match.group(1)) if listing_match else 0

            # 参考价
            price_elem = dd.select_one(".pm-rate")
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            price_match = re.search(r"([\d,]+)", price_text)
            price = float(price_match.group(1).replace(",", "")) if price_match else 0

            if community_name and price > 0:
                ranking.append({
                    "rank": int(rank_text),
                    "community": community_name,
                    "listing_count": listing_count,
                    "price": price,
                })

        return ranking
