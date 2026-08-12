"""
对 utils/dummy_data.py 的单元测试
覆盖：_get_base_price、_get_communities
"""
import unittest
import sys
import os

# 确保可以导入 src 模块
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from src.utils.dummy_data import _get_base_price, _get_communities


class TestGetBasePrice(unittest.TestCase):
    """_get_base_price 的单元测试：基准价格计算"""

    def test_一环买房基准(self):
        """一环别墅买房基准价应为 27000（基于房天下真实数据）"""
        price = _get_base_price("一环", "别墅", "buy")
        self.assertAlmostEqual(price, 27000, delta=1)

    def test_一环租房基准(self):
        """一环别墅租房基准价应为 4000"""
        price = _get_base_price("一环", "别墅", "rent")
        self.assertAlmostEqual(price, 4000, delta=1)

    def test_五环比一环便宜(self):
        """五环价格应低于一环（向外递减）"""
        price_yihuan = _get_base_price("一环", "高层", "buy")
        price_wuhuan = _get_base_price("五环", "高层", "buy")
        self.assertGreater(price_yihuan, price_wuhuan)

    def test_二环价格在一环五环之间(self):
        """二环价格应在一环和五环之间"""
        price_yihuan = _get_base_price("一环", "洋房", "buy")
        price_erhuan = _get_base_price("二环", "洋房", "buy")
        price_wuhuan = _get_base_price("五环", "洋房", "buy")
        self.assertGreater(price_yihuan, price_erhuan)
        self.assertGreater(price_erhuan, price_wuhuan)

    def test_租房比买房便宜(self):
        """同一区域同一类型，租房价格应远低于买房"""
        price_buy = _get_base_price("一环", "高层", "buy")
        price_rent = _get_base_price("一环", "高层", "rent")
        self.assertGreater(price_buy, price_rent)

    def test_不存在的类型返回默认(self):
        """不在配置中的类型应返回默认值 10000"""
        price = _get_base_price("一环", "不存在类型", "buy")
        self.assertAlmostEqual(price, 10000, delta=1)

    def test_不存在的区域返回最低系数(self):
        """不在配置中的区域返回默认系数 0.8"""
        price_known = _get_base_price("一环", "高层", "buy")  # 系数1.0
        price_unknown = _get_base_price("外环", "高层", "buy")  # 系数0.8
        self.assertGreater(price_known, price_unknown)


class TestGetCommunities(unittest.TestCase):
    """_get_communities 的单元测试：参考小区列表"""

    def test_一环别墅有小区列表(self):
        """一环别墅应返回非空小区列表"""
        communities = _get_communities("一环", "别墅")
        self.assertIsInstance(communities, list)
        self.assertGreater(len(communities), 0)

    def test_每种类型都有小区(self):
        """每个区域的每种类型都应返回小区列表"""
        for region in ["一环", "二环", "三环", "四环", "五环"]:
            for ctype in ["别墅", "洋房", "高层"]:
                communities = _get_communities(region, ctype)
                self.assertGreater(len(communities), 0,
                                   f"{region}/{ctype} 不应返回空列表")

    def test_不存在的区域类型返回默认值(self):
        """未知的区域+类型组合，返回默认小区名"""
        communities = _get_communities("未知区域", "未知类型")
        self.assertEqual(len(communities), 1)
        self.assertIn("未知区域", communities[0])

    def test_小区名均为字符串(self):
        """返回的所有小区名都是字符串"""
        communities = _get_communities("二环", "高层")
        for name in communities:
            self.assertIsInstance(name, str)


if __name__ == "__main__":
    unittest.main()
