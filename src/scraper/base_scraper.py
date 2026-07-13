"""
张家港房价App — 爬虫基类
所有数据源爬虫继承此基类，共用合规检查和错误处理
"""

import time
import urllib.robotparser
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional

import requests

from src.utils.config import SCRAPER_CONFIG
from src.utils.logger import get_logger

logger = get_logger("scraper")


class BaseScraper(ABC):
    """
    爬虫基类，所有数据源的爬虫必须继承此类。

    提供了以下公共能力：
    - robots.txt 合规检查（check_robots）
    - 受控 HTTP 请求（fetch_page）—— 自动限流、重试、UA标识
    - 统一的日志和错误处理
    - 数据格式校验
    """

    # 该爬虫抓取的数据类型：'buy'=买房(元/㎡), 'rent'=租房(元/月)
    # 子类应覆盖此属性以声明自己抓取哪种数据
    scrape_data_type: str = "buy"

    def __init__(self, source_name: str, base_url: str):
        """
        初始化爬虫基类。

        参数:
            source_name: 数据源名称（如"安居客"）
            base_url: 数据源的基础URL
        """
        self.source_name = source_name
        self.base_url = base_url
        self.config = SCRAPER_CONFIG
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        # robots.txt 解析器
        self._rp = None
        self._consecutive_failures = 0

    def check_robots(self, url: str) -> bool:
        """
        检查目标 URL 是否允许爬虫访问（遵守 robots.txt）。

        参数:
            url: 要检查的目标URL

        返回:
            True 表示允许访问，False 表示被禁止
        """
        try:
            # 从 base_url 提取 domain
            from urllib.parse import urlparse
            parsed = urlparse(self.base_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            if self._rp is None:
                self._rp = urllib.robotparser.RobotFileParser()
                self._rp.set_url(robots_url)
                self._rp.read()

            allowed = self._rp.can_fetch(self.config["user_agent"], url)
            if not allowed:
                logger.warning(f"[robots.txt] 禁止访问: {url}")
            return allowed
        except Exception as e:
            # 如果 robots.txt 不可达，保守起见允许访问（很多网站robots.txt不稳定）
            logger.warning(f"读取 robots.txt 失败（{e}），默认允许访问")
            return True

    def fetch_page(self, url: str, params: Dict = None) -> Optional[str]:
        """
        受控的 HTTP GET 请求，自动执行限流和重试机制。

        限流规则（遵守爬虫合规）：
        - 每次请求间隔 ≥ 5秒
        - 403/429 自动等待60秒
        - 连续失败3次暂停60秒
        - 失败自动重试最多3次

        参数:
            url: 请求的URL
            params: URL查询参数

        返回:
            页面HTML内容，全部失败返回 None
        """
        # robots.txt 检查
        if not self.check_robots(url):
            return None

        # 限流：请求间隔 ≥ 5秒
        time.sleep(self.config["request_delay"])

        for attempt in range(1, self.config["max_retries"] + 1):
            try:
                logger.debug(f"[{self.source_name}] 请求 {url} (第{attempt}次)")
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config["timeout"]
                )

                # 处理被限制的响应
                if response.status_code in (403, 429):
                    logger.warning(
                        f"[{self.source_name}] 被限制 (HTTP {response.status_code})，"
                        f"等待 {self.config['wait_on_blocked']}秒"
                    )
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= self.config["max_retries"]:
                        logger.error(
                            f"[{self.source_name}] 连续失败{self.config['max_retries']}次，"
                            f"暂停当天抓取"
                        )
                        return None
                    time.sleep(self.config["wait_on_blocked"])
                    continue

                # 成功响应
                if response.status_code == 200:
                    self._consecutive_failures = 0
                    response.encoding = response.apparent_encoding or "utf-8"
                    return response.text

                # 其他HTTP错误
                logger.warning(
                    f"[{self.source_name}] HTTP {response.status_code}: {url}"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"[{self.source_name}] 请求超时: {url}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"[{self.source_name}] 连接失败: {url}")
            except requests.exceptions.RequestException as e:
                logger.error(f"[{self.source_name}] 请求异常: {e}")

            # 重试等待
            if attempt < self.config["max_retries"]:
                wait = self.config["request_delay"] * attempt
                logger.info(f"[{self.source_name}] {wait}秒后重试...")
                time.sleep(wait)

        # 全部重试失败
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.config["max_retries"]:
            logger.error(
                f"[{self.source_name}] 连续失败{self.config['max_retries']}次，暂停当天抓取"
            )
        return None

    @abstractmethod
    def scrape(self) -> List[Dict]:
        """
        执行数据抓取，子类必须实现此方法。

        返回:
            抓取到的价格数据列表，格式如下：
            [
                {
                    "date": "2026-07-13",
                    "region": "一环",
                    "community": "小区名",
                    "price": 15426.0,
                    "unit": "元/㎡",
                    "source": "安居客",
                },
                ...
            ]
        """
        pass

    def validate_record(self, record: Dict) -> bool:
        """
        校验一条数据记录的格式是否正确。

        参数:
            record: 数据字典

        返回:
            数据格式是否合法
        """
        required_fields = ["date", "region", "price", "source"]
        for field in required_fields:
            if field not in record or record[field] is None:
                logger.warning(f"数据缺少必要字段 {field}: {record}")
                return False

        # 价格必须是数字且合理
        # 根据爬虫类型使用不同的价格范围校验
        price = record.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            logger.warning(f"价格数据异常: {price}")
            return False

        # 根据数据类型校验价格范围
        record_data_type = record.get("data_type", self.scrape_data_type)
        if record_data_type == "rent":
            # 张家港租房合理范围：100-10000 元/月
            if price > 10000:
                logger.warning(f"租房价格异常（超过10000元/月）: {price}")
                return False
        else:
            # 张家港买房合理范围：1000-100000 元/㎡
            if price > 100000:
                logger.warning(f"买房价格异常（超过100000元/㎡）: {price}")
                return False

        # 日期格式校验
        try:
            datetime.strptime(record["date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            logger.warning(f"日期格式错误: {record.get('date')}")
            return False

        return True
