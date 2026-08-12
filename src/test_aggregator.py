"""
对 utils/aggregator.py 的单元测试
覆盖：_safe_median、_remove_outliers、_group_by_source
"""
import unittest
import sys
import os

# 确保可以导入 src 模块
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from src.utils.aggregator import _safe_median, _remove_outliers, _group_by_source


class TestSafeMedian(unittest.TestCase):
    """_safe_median 的单元测试：安全计算中位数"""

    def test_正常奇数列表(self):
        """奇数个元素的列表，取中间值"""
        self.assertEqual(_safe_median([1, 2, 3]), 2)

    def test_正常偶数列表(self):
        """偶数个元素的列表，取中间两数平均"""
        self.assertEqual(_safe_median([1, 2, 3, 4]), 2.5)

    def test_单个元素(self):
        """只有一个元素时返回自身"""
        self.assertEqual(_safe_median([42]), 42)

    def test_空列表(self):
        """空列表返回 0.0"""
        self.assertEqual(_safe_median([]), 0.0)

    def test_未排序输入(self):
        """乱序输入不影响结果"""
        self.assertEqual(_safe_median([5, 1, 3]), 3)

    def test_含负数(self):
        """列表中含有负数也能正确计算"""
        self.assertEqual(_safe_median([-5, 0, 5]), 0)


class TestRemoveOutliers(unittest.TestCase):
    """_remove_outliers 的单元测试：异常值剔除（超过均值±30%的数据）"""

    def test_正常数据无剔除(self):
        """所有数据都在合理范围内，不剔除任何值"""
        prices = [100, 102, 98, 101, 99]
        result = _remove_outliers(prices)
        self.assertEqual(result, prices)

    def test_剔除明显异常值(self):
        """存在极端异常值（超过均值 ±30%）应被剔除"""
        # 5 个密集值集中在 ~10000，1 个极端值 30000
        prices = [9800, 9900, 10000, 10100, 10200, 30000]
        result = _remove_outliers(prices)
        # 30000 超出 avg*1.3 应被剔除
        self.assertNotIn(30000, result)
        # 正常值 5 个全部保留
        self.assertEqual(len(result), 5)

    def test_少于3条不剔除(self):
        """2条及以下数据不做剔除，原样返回（样本太少无法判断异常）"""
        prices = [100, 10000]
        result = _remove_outliers(prices)
        self.assertEqual(result, prices)

    def test_空列表(self):
        """空列表不报错，返回空列表"""
        self.assertEqual(_remove_outliers([]), [])

    def test_全部异常值保留原样(self):
        """如果剔除后列表为空（全是异常值），保留原始数据避免数据丢失"""
        prices = [1, 1000, 2000]  # 彼此相差大，可能全部被剔除
        result = _remove_outliers(prices)
        # 如果剔除后为空，应返回原始列表
        self.assertTrue(len(result) >= 1)


class TestGroupBySource(unittest.TestCase):
    """_group_by_source 的单元测试：按数据源分组"""

    def test_正常分组(self):
        """多条不同来源的记录，按 source 字段分组"""
        records = [
            {"source": "安居客", "price": 100},
            {"source": "贝壳", "price": 105},
            {"source": "安居客", "price": 98},
        ]
        groups = _group_by_source(records)
        self.assertIn("安居客", groups)
        self.assertIn("贝壳", groups)
        self.assertEqual(len(groups["安居客"]), 2)
        self.assertEqual(len(groups["贝壳"]), 1)

    def test_空列表(self):
        """空记录返回空字典"""
        self.assertEqual(_group_by_source([]), {})

    def test_单条记录(self):
        """只有一条记录时，返回只有一个 key 的字典"""
        records = [{"source": "链家", "price": 120}]
        groups = _group_by_source(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups["链家"][0]["price"], 120)

    def test_缺source字段(self):
        """记录缺少 source 字段时，归入'未知'分组"""
        records = [{"price": 100}]
        groups = _group_by_source(records)
        self.assertIn("未知", groups)


if __name__ == "__main__":
    unittest.main()
