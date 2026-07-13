"""
张家港房价App — 动态页面爬虫基类
用于需要JavaScript渲染的页面（贝壳、链家等）
"""

import time
from abc import abstractmethod
from typing import List, Dict, Optional

from src.scraper.base_scraper import BaseScraper
from src.utils.config import SCRAPER_CONFIG
from src.utils.logger import get_logger

logger = get_logger("scraper.dynamic")


class DynamicScraper(BaseScraper):
    """
    动态页面爬虫基类，使用 Playwright 渲染JavaScript页面。

    使用方式：
    1. 继承此类，实现 parse_prices(page) 方法
    2. 在 scrape() 中调用 scrape_dynamic()
    """

    def __init__(self, source_name: str, base_url: str):
        super().__init__(source_name, base_url)
        self.playwright = None
        self.browser = None

    def _init_browser(self):
        """
        初始化 Playwright 浏览器实例。
        使用无头模式，不需要打开真正的浏览器窗口。
        """
        try:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            logger.info(f"[{self.source_name}] Playwright 浏览器已启动")
        except ImportError:
            logger.error("Playwright 未安装，请运行: pip install playwright && playwright install chromium")
            raise
        except Exception as e:
            logger.error(f"Playwright 启动失败: {e}")
            raise

    def _close_browser(self):
        """关闭浏览器实例，释放资源。"""
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        logger.debug(f"[{self.source_name}] 浏览器已关闭")

    def fetch_dynamic_page(self, url: str, wait_selector: str = "", wait_time: int = 3) -> Optional[str]:
        """
        使用 Playwright 获取动态页面的渲染后HTML。

        参数:
            url: 目标URL
            wait_selector: 等待的CSS选择器（确保内容渲染完成）
            wait_time: 最大等待时间（秒）

        返回:
            页面HTML内容，失败返回 None
        """
        # 限流
        time.sleep(SCRAPER_CONFIG["request_delay"])

        try:
            if not self.browser:
                self._init_browser()

            page = self.browser.new_page(
                user_agent=SCRAPER_CONFIG["user_agent"]
            )

            # 设置超时
            page.set_default_timeout(SCRAPER_CONFIG["timeout"] * 1000)

            # 导航到页面
            page.goto(url, wait_until="domcontentloaded")

            # 等待指定选择器出现（确保动态内容加载）
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=wait_time * 1000)
                except Exception:
                    logger.warning(f"[{self.source_name}] 等待选择器超时: {wait_selector}")
            else:
                # 默认等待页面加载
                page.wait_for_load_state("networkidle", timeout=wait_time * 1000)

            # 获取渲染后的HTML
            html = page.content()
            page.close()

            return html

        except Exception as e:
            logger.error(f"[{self.source_name}] 动态页面获取失败: {e}")
            return None

    @abstractmethod
    def parse_prices(self, html: str, region_name: str, date: str) -> List[Dict]:
        """
        从HTML中解析价格数据。子类必须实现。

        参数:
            html: 页面HTML内容
            region_name: 区域名称
            date: 当前日期

        返回:
            价格数据列表
        """
        pass

    def scrape_dynamic(self, region_urls: Dict[str, str],
                       wait_selector: str = "") -> List[Dict]:
        """
        批量抓取多个区域的动态页面数据。

        参数:
            region_urls: 区域名称到URL的映射
            wait_selector: 每个页面等待的CSS选择器

        返回:
            所有区域的价格数据列表
        """
        all_records = []

        try:
            for region_name, url in region_urls.items():
                try:
                    html = self.fetch_dynamic_page(url, wait_selector)
                    if html:
                        today = time.strftime("%Y-%m-%d")
                        records = self.parse_prices(html, region_name, today)
                        all_records.extend(records)
                        logger.info(f"[{self.source_name}] {region_name}: {len(records)} 条")
                except Exception as e:
                    logger.error(f"[{self.source_name}] {region_name} 失败: {e}")
        finally:
            # 确保浏览器关闭
            # 注意：这里不关闭以便复用，在管理器中统一管理生命周期
            pass

        return all_records
