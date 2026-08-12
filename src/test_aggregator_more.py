"""
对 utils/aggregator.py 的扩展单元测试
覆盖：aggregate_daily_prices、get_chart_data、get_region_summary
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# 确保可以导入 src 模块
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import src.data.database as db_module
from src.utils.logger import get_logger

logger = get_logger("test.aggregator_more")


class TestAggregateDailyPrices(unittest.TestCase):
    """aggregate_daily_prices 单元测试"""

    def setUp(self):
        """创建临时数据库并填充测试数据"""
        self.original_path = db_module.DATABASE_PATH
        db_module.close_connection()
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        db_module.DATABASE_PATH = self.temp_db.name
        db_module.init_database()

        # 插入测试数据：一环/高层/买房，两个数据源
        self.test_date = "2026-08-12"
        db_module.insert_raw_price(
            self.test_date, "一环", "小区A", 15000.0, "源1",
            community_type="高层", data_type="buy"
        )
        db_module.insert_raw_price(
            self.test_date, "一环", "小区B", 15200.0, "源1",
            community_type="高层", data_type="buy"
        )
        db_module.insert_raw_price(
            self.test_date, "一环", "小区C", 15500.0, "源2",
            community_type="高层", data_type="buy"
        )

    def tearDown(self):
        """恢复原始数据库路径"""
        db_module.close_connection()
        db_module.DATABASE_PATH = self.original_path
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_聚合有数据(self):
        """有数据时应返回OHLC结果"""
        from src.utils.aggregator import aggregate_daily_prices
        result = aggregate_daily_prices(self.test_date, "一环", "高层", data_type="buy")
        self.assertIsNotNone(result)
        self.assertIn("open_price", result)
        self.assertIn("close_price", result)
        self.assertIn("high_price", result)
        self.assertIn("low_price", result)

    def test_聚合无数据返回None(self):
        """没有数据时应返回None"""
        from src.utils.aggregator import aggregate_daily_prices
        result = aggregate_daily_prices("2000-01-01", "一环", "高层", data_type="buy")
        self.assertIsNone(result)

    def test_聚合结果写入数据库(self):
        """聚合后数据应写入OHLC表"""
        from src.utils.aggregator import aggregate_daily_prices
        aggregate_daily_prices(self.test_date, "一环", "高层", data_type="buy")

        latest = db_module.get_latest_ohlc("一环", "高层", data_type="buy")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["date"], self.test_date)

    def test_聚合租房数据(self):
        """租房数据聚合应正常"""
        from src.utils.aggregator import aggregate_daily_prices
        # 插入租房数据
        db_module.insert_raw_price(
            self.test_date, "一环", "小区A", 1200.0, "源1",
            community_type="高层", data_type="rent"
        )
        result = aggregate_daily_prices(self.test_date, "一环", "高层", data_type="rent")
        self.assertIsNotNone(result)


class TestGetChartData(unittest.TestCase):
    """get_chart_data 单元测试"""

    def setUp(self):
        """创建临时数据库并填充OHLC数据"""
        self.original_path = db_module.DATABASE_PATH
        db_module.close_connection()
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        db_module.DATABASE_PATH = self.temp_db.name
        db_module.init_database()

        # 插入3天OHLC数据（source_count 整数）
        for day in ["2026-08-10", "2026-08-11", "2026-08-12"]:
            db_module.insert_ohlc(
                day, "一环", "高层",
                15000, 15500, 14800, 15200, 15100, 10, source_count=2,
                data_type="buy"
            )

    def tearDown(self):
        """恢复原始数据库路径"""
        db_module.close_connection()
        db_module.DATABASE_PATH = self.original_path
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_获取图表数据(self):
        """应返回完整的图表数据结构"""
        from src.utils.aggregator import get_chart_data
        data = get_chart_data("一环", "高层", days=30, data_type="buy")
        self.assertEqual(data["region"], "一环")
        self.assertEqual(data["community_type"], "高层")
        self.assertEqual(len(data["dates"]), 3)
        self.assertEqual(len(data["ohlcs"]), 3)
        self.assertIsNotNone(data["latest"])

    def test_空数据返回默认结构(self):
        """没有数据时应返回空结构"""
        from src.utils.aggregator import get_chart_data
        data = get_chart_data("三环", "别墅", days=30, data_type="buy")
        self.assertEqual(data["dates"], [])
        self.assertIsNone(data["latest"])

    def test_涨跌计算(self):
        """两天数据应能计算涨跌幅"""
        from src.utils.aggregator import get_chart_data
        data = get_chart_data("一环", "高层", days=30, data_type="buy")
        # 有3天数据，应能计算涨跌
        self.assertIn("change_pct", data)


class TestGetRegionSummary(unittest.TestCase):
    """get_region_summary 单元测试"""

    def setUp(self):
        """创建临时数据库"""
        self.original_path = db_module.DATABASE_PATH
        db_module.close_connection()
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        db_module.DATABASE_PATH = self.temp_db.name
        db_module.init_database()

    def tearDown(self):
        """恢复原始数据库路径"""
        db_module.close_connection()
        db_module.DATABASE_PATH = self.original_path
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_汇总返回列表(self):
        """应返回汇总列表"""
        from src.utils.aggregator import get_region_summary
        # 插入一些数据（source_count 整数）
        db_module.insert_ohlc(
            "2026-08-12", "一环", "高层",
            15000, 15500, 14800, 15200, 15100, 10, source_count=1,
            data_type="buy"
        )
        summary = get_region_summary("一环", days=30, data_type="buy")
        self.assertIsInstance(summary, list)
        if summary:
            self.assertIn("type", summary[0])
            self.assertIn("avg_price", summary[0])


if __name__ == "__main__":
    unittest.main()
