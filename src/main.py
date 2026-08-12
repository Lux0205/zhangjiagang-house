"""
张家港房价K线图软件 - 程序入口
运行此文件启动桌面软件

用法: python main.py

优化：精简启动流程，减少初始化时间
"""

import sys
import os

# 确保项目根目录始终在 Python 路径最前面
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

for p in list(sys.path):
    if p and os.path.isdir(p) and os.path.samefile(p, SCRIPT_DIR):
        sys.path.remove(p)

if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


def main():
    """
    程序入口函数。
    1. 初始化配置和数据库
    2. 启动 PyQt6 应用
    3. 显示主窗口
    """
    # PyQt6 + QtWebEngine 初始化
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    # 设置 OpenGL 共享（QtWebEngine 需要）
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("张家港房价K线图")
    app.setApplicationVersion("1.0.0")

    # 延迟导入：只在需要时才加载模块，减少启动时间和内存
    from src.utils.logger import get_logger
    logger = get_logger("app")
    logger.info("张家港房价K线图软件 启动")

    # 初始化数据库（会自动创建表）
    from src.data.database import init_database, close_connection
    init_database()
    logger.info("数据库已就绪")

    # 首次运行：填充假数据保证离线可用
    from src.utils.dummy_data import ensure_data_available
    dummy_count = ensure_data_available()
    if dummy_count > 0:
        logger.info(f"首次运行，已填充 {dummy_count} 条演示数据")
    else:
        logger.info("数据库已有数据，跳过演示数据填充")

    # 创建并显示主窗口
    from src.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    logger.info("主窗口已显示")

    # 进入Qt事件循环
    exit_code = app.exec()

    # 退出时清理数据库连接
    close_connection()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
