"""
对 utils/config.py 的单元测试
覆盖：配置常量完整性、区域因子、数据类型定义
"""
import unittest
import os
import sys

# 确保可以导入 src 模块
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from src.utils.config import (
    REGION_NAMES, COMMUNITY_TYPE_NAMES, DATA_TYPES, DATA_TYPE_NAMES,
    BUY_BASE_PRICES, RENT_BASE_PRICES, REGION_FACTORS,
    COMMUNITY_TYPE_FACTORS, DATA_TYPE_UNIT,
    SCRAPER_CONFIG, AGGREGATOR_CONFIG, UI_CONFIG,
    REGIONS, COMMUNITY_TYPES, SCRAPER_SOURCES,
)


class TestConfigConstants(unittest.TestCase):
    """配置常量完整性测试"""

    def test_区域名称完整(self):
        """应有5个环的区域名称"""
        self.assertEqual(len(REGION_NAMES), 5)
        self.assertIn("一环", REGION_NAMES)
        self.assertIn("五环", REGION_NAMES)

    def test_小区类型完整(self):
        """应有5种小区类型"""
        self.assertEqual(len(COMMUNITY_TYPE_NAMES), 5)
        self.assertIn("别墅", COMMUNITY_TYPE_NAMES)
        self.assertIn("高层", COMMUNITY_TYPE_NAMES)

    def test_数据类型定义(self):
        """应有买房和租房两种数据类型"""
        self.assertIn("buy", DATA_TYPES)
        self.assertIn("rent", DATA_TYPES)
        self.assertEqual(DATA_TYPES["buy"], "买房价格")
        self.assertEqual(DATA_TYPES["rent"], "租房价格")

    def test_数据类型单位(self):
        """买房单位为元/㎡，租房单位为元/月"""
        self.assertEqual(DATA_TYPE_UNIT["buy"], "元/㎡")
        self.assertEqual(DATA_TYPE_UNIT["rent"], "元/月")


class TestBasePrices(unittest.TestCase):
    """基准价格配置测试"""

    def test_买房基准价完整(self):
        """所有小区类型都应有买房基准价"""
        for ctype in COMMUNITY_TYPE_NAMES:
            self.assertIn(ctype, BUY_BASE_PRICES, f"{ctype} 缺少买房基准价")

    def test_租房基准价完整(self):
        """所有小区类型都应有租房基准价"""
        for ctype in COMMUNITY_TYPE_NAMES:
            self.assertIn(ctype, RENT_BASE_PRICES, f"{ctype} 缺少租房基准价")

    def test_买房基准价高于租房(self):
        """同一类型买房基准价应远高于租房"""
        for ctype in COMMUNITY_TYPE_NAMES:
            self.assertGreater(
                BUY_BASE_PRICES[ctype], RENT_BASE_PRICES[ctype],
                f"{ctype} 买房基准价应高于租房"
            )

    def test_别墅价格最高(self):
        """别墅基准价应是最高的"""
        for ctype in COMMUNITY_TYPE_NAMES:
            if ctype != "别墅":
                self.assertGreater(
                    BUY_BASE_PRICES["别墅"], BUY_BASE_PRICES[ctype],
                    "别墅应是最高价"
                )

    def test_基准价为正数(self):
        """所有基准价应为正数"""
        for ctype in COMMUNITY_TYPE_NAMES:
            self.assertGreater(BUY_BASE_PRICES[ctype], 0)
            self.assertGreater(RENT_BASE_PRICES[ctype], 0)


class TestRegionFactors(unittest.TestCase):
    """区域因子测试"""

    def test_一环因子为1(self):
        """一环区域因子应为1.0（基准）"""
        self.assertAlmostEqual(REGION_FACTORS["一环"], 1.0)

    def test_向外递减(self):
        """区域因子应从一环到五环递减"""
        prev = REGION_FACTORS["一环"]
        for region in ["二环", "三环", "四环", "五环"]:
            self.assertLess(
                REGION_FACTORS[region], prev,
                f"{region} 因子应小于前一环"
            )
            prev = REGION_FACTORS[region]

    def test_所有区域都有因子(self):
        """每个区域都应有对应的因子"""
        for region in REGION_NAMES:
            self.assertIn(region, REGION_FACTORS)


class TestCommunityTypeFactors(unittest.TestCase):
    """小区类型系数测试"""

    def test_高层系数为1(self):
        """高层类型系数应为1.0（基准）"""
        self.assertAlmostEqual(COMMUNITY_TYPE_FACTORS["高层"], 1.0)

    def test_别墅系数最高(self):
        """别墅系数应是最大的"""
        for ctype in COMMUNITY_TYPE_NAMES:
            if ctype != "别墅":
                self.assertGreater(
                    COMMUNITY_TYPE_FACTORS["别墅"],
                    COMMUNITY_TYPE_FACTORS[ctype]
                )


class TestScraperConfig(unittest.TestCase):
    """爬虫配置测试"""

    def test_请求间隔至少5秒(self):
        """请求间隔应≥5秒（遵守robots.txt）"""
        self.assertGreaterEqual(SCRAPER_CONFIG["request_delay"], 5)

    def test_超时时间为正(self):
        """超时时间应为正数"""
        self.assertGreater(SCRAPER_CONFIG["timeout"], 0)

    def test_有User_Agent(self):
        """应配置User-Agent"""
        self.assertIn("user_agent", SCRAPER_CONFIG)
        self.assertTrue(len(SCRAPER_CONFIG["user_agent"]) > 0)

    def test_数据源配置完整(self):
        """6个数据源都应配置"""
        expected_sources = ["anjuke", "fang", "zjgzf", "ke", "lianjia", "tongcheng58"]
        for src in expected_sources:
            self.assertIn(src, SCRAPER_SOURCES, f"缺少数据源 {src} 的配置")


if __name__ == "__main__":
    unittest.main()
