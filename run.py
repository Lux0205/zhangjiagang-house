# -*- coding: utf-8 -*-
"""
张家港房价K线图软件 - 启动脚本
双击此文件即可启动软件，避免中文路径编码问题
"""
import os
import sys

# 切换到脚本所在目录（项目根目录）
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 执行主程序
from src.main import main

if __name__ == "__main__":
    main()
