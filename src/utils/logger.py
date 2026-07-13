"""
张家港房价App - 日志模块
统一管理程序运行日志
"""

import logging
import os
from datetime import datetime

# 日志目录：项目根目录下的 logs 文件夹
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_UTILS_DIR = os.path.dirname(_THIS_DIR)
_SRC_DIR = os.path.dirname(_UTILS_DIR)
_PROJECT_DIR = os.path.dirname(_SRC_DIR)
LOG_DIR = os.path.join(_PROJECT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件名（按日期）
_TODAY = datetime.now().strftime("%Y%m%d")
LOG_FILE = os.path.join(LOG_DIR, f"house_{_TODAY}.log")


def get_logger(name: str = "house_app") -> logging.Logger:
    """
    获取一个配置好的日志记录器。

    参数:
        name: 日志记录器名称，默认 "house_app"

    返回:
        logging.Logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 文件处理器 - 记录所有级别
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # 控制台处理器 - 只显示 INFO 及以上
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 格式
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
