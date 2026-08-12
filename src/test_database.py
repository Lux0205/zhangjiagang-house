"""
对 data/database.py 的单元测试
覆盖：insert_raw_price、insert_raw_prices_batch、get_raw_prices、
      insert_ohlc、get_ohlc_by_region_type、get_latest_ohlc、get_last_update_time
"""
import unittest
import os
import sys
import tempfile
import sqlite3

# 确保可以导入 src 模块
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# 使用临时数据库进行测试
import src.data.database as db_module
from src.utils.logger import get_logger

logger = get_logger("test.database")


class TestDatabaseOperations(unittest.TestCase):
    """数据库操作单元测试（使用临时数据库）"""

    def setUp(self):
        """每个测试前创建临时数据库"""
        self.original_path = db_module.DATABASE_PATH
        # 先关闭旧连接，避免临时文件被占用
        db_module.close_connection()
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()  # 关闭文件句柄，让 sqlite 可以独占
        db_module.DATABASE_PATH = self.temp_db.name
        db_module.init_database()

    def tearDown(self):
        """每个测试后恢复原始数据库路径并删除临时文件"""
        db_module.close_connection()  # 关闭连接释放文件锁
        db_module.DATABASE_PATH = self.original_path
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_插入单条原始价格(self):
        """插入一条买房价格应成功"""
        result = db_module.insert_raw_price(
            "2026-08-12", "一环", "测试小区", 15000.0, "测试源"
        )
        self.assertTrue(result)

    def test_插入租房价格(self):
        """插入一条租房价格应成功"""
        result = db_module.insert_raw_price(
            "2026-08-12", "一环", "测试小区", 1200.0,
            "测试源", data_type="rent"
        )
        self.assertTrue(result)

    def test_批量插入原始价格(self):
        """批量插入多条记录"""
        records = [
            {"date": "2026-08-12", "region": "一环", "community": "小区A",
             "price": 15000.0, "source": "源1", "data_type": "buy"},
            {"date": "2026-08-12", "region": "一环", "community": "小区B",
             "price": 16000.0, "source": "源2", "data_type": "buy"},
            {"date": "2026-08-12", "region": "二环", "community": "小区C",
             "price": 1200.0, "source": "源1", "data_type": "rent"},
        ]
        count = db_module.insert_raw_prices_batch(records)
        self.assertEqual(count, 3)

    def test_查询原始价格(self):
        """插入后能正确查询到"""
        db_module.insert_raw_price(
            "2026-08-12", "一环", "测试小区", 15000.0, "测试源",
            community_type="高层", data_type="buy"
        )
        results = db_module.get_raw_prices("2026-08-12", "一环", "高层", data_type="buy")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["price"], 15000.0)

    def test_查询不存在的日期返回空(self):
        """查询没有数据的日期应返回空列表"""
        results = db_module.get_raw_prices("2000-01-01", "一环", data_type="buy")
        self.assertEqual(results, [])

    def test_插入OHLC数据(self):
        """插入OHLC数据应成功（source_count 整数替代 sources 文本）"""
        result = db_module.insert_ohlc(
            "2026-08-12", "一环", "高层",
            15000, 15500, 14800, 15200, 15100, 10, source_count=2,
            data_type="buy"
        )
        self.assertTrue(result)

    def test_查询OHLC数据(self):
        """插入OHLC后能正确查询"""
        db_module.insert_ohlc(
            "2026-08-12", "一环", "高层",
            15000, 15500, 14800, 15200, 15100, 10, source_count=1,
            data_type="buy"
        )
        results = db_module.get_ohlc_by_region_type("一环", "高层", days=30, data_type="buy")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["close_price"], 15200)

    def test_查询最新OHLC(self):
        """查询最新OHLC应返回最近一天的数据"""
        db_module.insert_ohlc(
            "2026-08-10", "一环", "高层",
            15000, 15500, 14800, 15200, 15100, 10, source_count=1,
            data_type="buy"
        )
        db_module.insert_ohlc(
            "2026-08-12", "一环", "高层",
            15200, 15800, 15100, 15600, 15500, 12, source_count=2,
            data_type="buy"
        )
        latest = db_module.get_latest_ohlc("一环", "高层", data_type="buy")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["date"], "2026-08-12")

    def test_查询最后更新时间(self):
        """插入数据后能获取到最后更新日期"""
        db_module.insert_ohlc(
            "2026-08-12", "一环", "高层",
            15000, 15500, 14800, 15200, 15100, 10, source_count=1,
            data_type="buy"
        )
        last_date = db_module.get_last_update_time(data_type="buy")
        self.assertEqual(last_date, "2026-08-12")

    def test_唯一约束_重复插入被忽略(self):
        """重复插入相同唯一键的数据应被忽略（不报错）"""
        db_module.insert_raw_price(
            "2026-08-12", "一环", "测试小区", 15000.0, "测试源"
        )
        # 再次插入相同数据（唯一键冲突）
        result = db_module.insert_raw_price(
            "2026-08-12", "一环", "测试小区", 99999.0, "测试源"
        )
        # 不应报错，且数据库中仍是原始值
        results = db_module.get_raw_prices("2026-08-12", "一环", data_type="buy")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["price"], 15000.0)

    def test_buy和rent数据隔离(self):
        """买房和租房数据应相互隔离"""
        db_module.insert_raw_price(
            "2026-08-12", "一环", "测试小区", 15000.0, "测试源", data_type="buy"
        )
        db_module.insert_raw_price(
            "2026-08-12", "一环", "测试小区", 1200.0, "测试源", data_type="rent"
        )
        buy_results = db_module.get_raw_prices("2026-08-12", "一环", data_type="buy")
        rent_results = db_module.get_raw_prices("2026-08-12", "一环", data_type="rent")
        self.assertEqual(len(buy_results), 1)
        self.assertEqual(len(rent_results), 1)
        self.assertEqual(buy_results[0]["price"], 15000.0)
        self.assertEqual(rent_results[0]["price"], 1200.0)


if __name__ == "__main__":
    unittest.main()
