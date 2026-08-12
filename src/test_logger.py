"""
对 utils/logger.py 的单元测试
覆盖：get_logger
"""
import unittest
import logging
import sys
import os

# 确保可以导入 src 模块
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from src.utils.logger import get_logger


class TestGetLogger(unittest.TestCase):
    """get_logger 的单元测试：获取日志记录器"""

    def test_返回Logger实例(self):
        """调用 get_logger 应返回 logging.Logger 对象"""
        logger = get_logger("test")
        self.assertIsInstance(logger, logging.Logger)

    def test_相同名称返回同一实例(self):
        """相同 name 的调用应返回同一个 Logger（单例）"""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        self.assertIs(logger1, logger2)

    def test_不同名称返回不同实例(self):
        """不同 name 应返回不同的 Logger"""
        logger1 = get_logger("name_a")
        logger2 = get_logger("name_b")
        self.assertIsNot(logger1, logger2)

    def test_默认名称(self):
        """不传参数时使用默认名称"""
        logger = get_logger()
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "house_app")

    def test_可正常记录日志(self):
        """获取的 logger 应能正常输出日志（不报错）"""
        logger = get_logger("log_test")
        try:
            logger.info("这是一条测试日志")
            logger.debug("这是一条 debug 日志")
            logger.warning("这是一条 warning 日志")
        except Exception as e:
            self.fail(f"日志记录不应该报错，但抛出了: {e}")


if __name__ == "__main__":
    unittest.main()
