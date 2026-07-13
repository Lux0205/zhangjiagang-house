"""
张家港房价App — PyInstaller 打包脚本
将程序打包为 Windows .exe 可执行文件

用法: python build.py

前提: 已安装 pyinstaller (pip install pyinstaller)
输出: dist/张家港房价K线图.exe
"""

import os
import sys
import shutil

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 输出配置
APP_NAME = "张家港房价K线图"
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "src", "main.py")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
SPEC_FILE = os.path.join(PROJECT_ROOT, f"{APP_NAME}.spec")


def clean_previous_build():
    """清理之前的打包产物"""
    dirs_to_clean = ["build", "dist"]
    for d in dirs_to_clean:
        path = os.path.join(PROJECT_ROOT, d)
        if os.path.exists(path):
            print(f"清理: {path}")
            shutil.rmtree(path)

    if os.path.exists(SPEC_FILE):
        os.remove(SPEC_FILE)


def build():
    """执行 PyInstaller 打包"""
    import PyInstaller.__main__

    print(f"开始打包: {APP_NAME}")
    print(f"主脚本: {MAIN_SCRIPT}")

    args = [
        MAIN_SCRIPT,                           # 要打包的入口脚本
        "--name", APP_NAME,                     # exe 文件名
        "--onefile",                            # 打包成单个 exe 文件
        "--windowed",                           # 不显示控制台窗口（GUI程序）
        "--noconfirm",                          # 不询问确认
        "--clean",                              # 清理临时文件
        # 包含 src 目录（所有项目源码在里面）
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'src')}{os.pathsep}src",
    ]

    # 如果资源目录存在也包含进去
    for resource_dir in ["docs", "logs"]:
        full_path = os.path.join(PROJECT_ROOT, resource_dir)
        if os.path.exists(full_path):
            args.extend([
                "--add-data", f"{full_path}{os.pathsep}{resource_dir}"
            ])

    PyInstaller.__main__.run(args)

    exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n✅ 打包成功！")
        print(f"文件路径: {exe_path}")
        print(f"文件大小: {size_mb:.1f} MB")
    else:
        print("❌ 打包失败，未找到输出文件")


def verify_build():
    """验证打包结果"""
    exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    if os.path.exists(exe_path):
        print(f"✅ 验证通过: {exe_path} 存在")
        return True
    else:
        print(f"❌ 验证失败: {exe_path} 不存在")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("张家港房价App — PyInstaller 打包")
    print("=" * 60)

    # 先清理旧产物
    clean_previous_build()

    # 执行打包
    try:
        build()
        verify_build()
    except ImportError:
        print("❌ 未安装 PyInstaller!")
        print("请运行: pip install pyinstaller")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 打包出错: {e}")
        sys.exit(1)
