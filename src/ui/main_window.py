"""
张家港房价App - 主窗口
包含：区域切换按钮 / 小区类型切换 / K线图 / 刷新 / 各类型汇总信息 / 免责声明
"""

from datetime import datetime
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QProgressBar,
    QFrame, QGroupBox, QMessageBox, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QWaitCondition, QMutex
from PyQt6.QtGui import QFont

from src.ui.chart_widget import ChartWidget
from src.utils.config import (
    REGION_NAMES, UI_CONFIG, DISCLAIMER, COMMUNITY_TYPE_NAMES
)
from src.utils.aggregator import get_chart_data, get_region_summary
from src.data.database import get_last_update_time
from src.scraper.manager import ScraperManager
from src.data.database import insert_raw_prices_batch
from src.utils.logger import get_logger

logger = get_logger("main_window")


class UpdateWorker(QThread):
    """后台工作线程"""
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)
    _stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.progress.emit("正在连接数据源...", 5)
            if self._stop_flag:
                return
            manager = ScraperManager()
            self.progress.emit("开始抓取数据(可能需要1-3分钟)...", 10)
            results = manager.run_all()
            all_records = manager.get_all_records()
            self.progress.emit(f"已抓取 {len(all_records)} 条原始数据...", 60)

            if all_records:
                insert_raw_prices_batch(all_records)

            self.progress.emit("正在计算聚合数据...", 80)
            from src.utils.aggregator import aggregate_all_regions_types
            aggregate_all_regions_types()
            self.progress.emit("更新完成！", 100)

            summary = manager.get_summary()
            msg = (f"成功更新！\n数据源: {summary['success_sources']}/{summary['total_sources']} 个成功\n"
                   f"数据量: {summary['total_records']} 条")
            self.finished.emit(True, msg)
        except Exception as e:
            logger.error(f"后台更新失败: {e}")
            self.finished.emit(False, f"更新失败: {e}")


class MainWindow(QMainWindow):
    """张家港房价K线图 - 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(UI_CONFIG["window_title"])
        self.setMinimumSize(1100, 750)
        self.resize(UI_CONFIG["window_width"], UI_CONFIG["window_height"])

        self.current_region = "一环"
        self.current_community_type = "高层"
        self.worker: Optional[UpdateWorker] = None

        self._setup_ui()
        self._apply_style()

        # 启动2秒后自动检查更新
        QTimer.singleShot(2000, self._auto_update_on_startup)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(6)

        # ===== 顶部工具栏 =====
        main_layout.addWidget(self._create_top_bar())

        # ===== 区域切换按钮 =====
        main_layout.addWidget(self._create_region_buttons())

        # ===== 小区类型切换按钮 =====
        main_layout.addWidget(self._create_type_buttons())

        # ===== K线图 =====
        self.chart_widget = ChartWidget()
        self.chart_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.chart_widget, stretch=1)

        # ===== 底部信息栏 =====
        main_layout.addWidget(self._create_bottom_bar())

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _create_top_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel("张家港房价 K线图")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(title)

        layout.addStretch()

        # 进度条
        self.update_progress = QProgressBar()
        self.update_progress.setMaximumWidth(180)
        self.update_progress.setMaximumHeight(18)
        self.update_progress.setVisible(False)
        layout.addWidget(self.update_progress)

        # 最后更新时间
        last_update = get_last_update_time()
        update_text = f"最后更新: {last_update}" if last_update else "尚未更新"
        self.update_time_label = QLabel(update_text)
        self.update_time_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.update_time_label)

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; border-radius: 4px;
                padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
            QPushButton:disabled { background-color: #555; color: #999; }
        """)
        self.refresh_btn.clicked.connect(self._on_manual_refresh)
        layout.addWidget(self.refresh_btn)

        return bar

    def _create_region_buttons(self) -> QWidget:
        """区域切换按钮：一环~五环"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 2)
        layout.setSpacing(4)

        label = QLabel("区域：")
        label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(label)

        self.region_buttons: Dict[str, QPushButton] = {}
        for region_name in REGION_NAMES:
            btn = QPushButton(region_name)
            btn.setCheckable(True)
            btn.setFixedSize(60, 28)
            btn.clicked.connect(lambda checked, r=region_name: self._on_region_clicked(r))
            self.region_buttons[region_name] = btn
            layout.addWidget(btn)

        layout.addStretch()
        self.region_buttons["一环"].setChecked(True)
        return bar

    def _create_type_buttons(self) -> QWidget:
        """小区类型切换按钮：别墅/洋房/高层/老小区/拆迁房"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 2)
        layout.setSpacing(4)

        label = QLabel("类型：")
        label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(label)

        self.type_buttons: Dict[str, QPushButton] = {}
        type_colors = {
            "别墅": "#E91E63",
            "洋房": "#FF9800",
            "高层": "#4CAF50",
            "老小区": "#9C27B0",
            "拆迁房": "#607D8B",
        }
        for type_name in COMMUNITY_TYPE_NAMES:
            btn = QPushButton(type_name)
            btn.setCheckable(True)
            btn.setFixedSize(65, 28)
            color = type_colors.get(type_name, "#4CAF50")
            btn._active_color = color
            btn.clicked.connect(lambda checked, t=type_name: self._on_type_clicked(t))
            self.type_buttons[type_name] = btn
            layout.addWidget(btn)

        layout.addStretch()
        self.type_buttons["高层"].setChecked(True)
        return bar

    def _create_bottom_bar(self) -> QWidget:
        bar = QWidget()
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(8, 2, 8, 6)

        # 当前选择 + 最新均价
        top_info = QHBoxLayout()

        self.region_info_label = QLabel("区域: 一环 | 类型: 高层")
        self.region_info_label.setStyleSheet("font-size: 13px; color: #e0e0e0; font-weight: bold;")
        top_info.addWidget(self.region_info_label)
        top_info.addStretch()

        self.price_info_label = QLabel("均价: -- 元/㎡")
        self.price_info_label.setStyleSheet("font-size: 14px; color: #4CAF50; font-weight: bold;")
        top_info.addWidget(self.price_info_label)
        top_info.addStretch()

        self.change_info_label = QLabel("30日涨跌: --")
        self.change_info_label.setStyleSheet("font-size: 13px;")
        top_info.addWidget(self.change_info_label)

        layout.addLayout(top_info)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #333;")
        layout.addWidget(line)

        # 各类型汇总对比
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 11px; color: #999; padding: 2px;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # 免责声明
        disc = QLabel(DISCLAIMER)
        disc.setStyleSheet("color: #666; font-size: 10px; padding: 2px;")
        disc.setWordWrap(True)
        disc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(disc)

        return bar

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QWidget { background-color: #1a1a2e; }
            QGroupBox {
                color: #aaa; border: 1px solid #333; border-radius: 4px;
                margin-top: 8px; padding-top: 8px;
            }
            QPushButton {
                background-color: #2a2a4a; color: #ccc;
                border: 1px solid #444; border-radius: 4px;
                padding: 3px 8px; font-size: 11px;
            }
            QPushButton:checked {
                background-color: #4CAF50; color: white; border-color: #4CAF50;
            }
            QPushButton:hover { background-color: #3a3a5a; }
            QLabel { color: #e0e0e0; }
            QProgressBar {
                background-color: #2a2a4a; border: none; border-radius: 2px;
            }
            QProgressBar::chunk { background-color: #4CAF50; }
            QStatusBar { background-color: #16162e; color: #888; }
        """)

    # ===== 事件处理 =====

    def _on_region_clicked(self, region_name: str):
        self.current_region = region_name
        for name, btn in self.region_buttons.items():
            btn.setChecked(name == region_name)
        self._load_chart_data(self.current_region, self.current_community_type)
        self._load_region_summary(self.current_region)

    def _on_type_clicked(self, type_name: str):
        self.current_community_type = type_name
        for name, btn in self.type_buttons.items():
            btn.setChecked(name == type_name)
        self._load_chart_data(self.current_region, self.current_community_type)

    def _on_manual_refresh(self):
        self._start_update(is_manual=True)

    def _auto_update_on_startup(self):
        last_update = get_last_update_time()
        today = datetime.now().strftime("%Y-%m-%d")

        # 先加载并显示已有数据，不阻塞界面显示
        self._load_chart_data(self.current_region, self.current_community_type)
        self._load_region_summary(self.current_region)

        if last_update == today:
            logger.info("今天已更新过数据，跳过自动更新")
        else:
            logger.info("今天尚未更新，3秒后开始自动更新...")
            # 延迟3秒等界面先显示出来
            QTimer.singleShot(3000, lambda: self._start_update(is_manual=False))

    def closeEvent(self, event):
        """关闭窗口时停止后台线程"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)  # 最多等2秒
        super().closeEvent(event)

    def _start_update(self, is_manual: bool = False):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "请稍候", "已有更新任务正在运行中。")
            return

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("更新中...")
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)
        self.status_bar.showMessage("正在更新数据...")

        self.worker = UpdateWorker()
        self.worker.progress.connect(self._on_update_progress)
        self.worker.finished.connect(lambda ok, msg: self._on_update_finished(ok, msg, is_manual))
        self.worker.start()

    def _on_update_progress(self, status: str, percent: int):
        self.update_progress.setValue(percent)
        self.status_bar.showMessage(f"正在更新... {status}")

    def _on_update_finished(self, success: bool, message: str, is_manual: bool):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("刷新数据")
        self.update_progress.setVisible(False)
        self.status_bar.showMessage("就绪")

        last_update = get_last_update_time()
        self.update_time_label.setText(f"最后更新: {last_update}")

        if is_manual:
            if success:
                QMessageBox.information(self, "更新完成", message)
            else:
                QMessageBox.warning(self, "更新失败", message)

        self._load_chart_data(self.current_region, self.current_community_type)
        self._load_region_summary(self.current_region)

    def _load_chart_data(self, region_name: str, community_type: str):
        """加载并显示某区域某类型的K线图"""
        try:
            data = get_chart_data(region_name, community_type, days=30)

            if data["dates"]:
                title = f"{region_name} - {community_type} 房价K线图 (近30天)"
                self.chart_widget.update_chart(
                    data["dates"], data["ohlcs"], data["volumes"], title
                )

                latest = data["latest"]
                close_price = latest["close_price"]
                change_pct = data["change_pct"]
                volume = latest["volume"]

                self.region_info_label.setText(
                    f"区域: {region_name} | 类型: {community_type} | 房源: {volume}套"
                )
                self.price_info_label.setText(f"均价: {close_price:,.0f} 元/㎡")

                if change_pct > 0:
                    self.change_info_label.setText(f"30日涨跌: +{change_pct:.2f}%")
                    self.change_info_label.setStyleSheet("font-size: 13px; color: #FF4444;")
                elif change_pct < 0:
                    self.change_info_label.setText(f"30日涨跌: {change_pct:.2f}%")
                    self.change_info_label.setStyleSheet("font-size: 13px; color: #00CC66;")
                else:
                    self.change_info_label.setText("30日涨跌: 持平")
                    self.change_info_label.setStyleSheet("font-size: 13px; color: #888;")

                logger.info(f"已加载 {region_name}/{community_type} K线图: {len(data['dates'])} 天")
            else:
                title = f"{region_name} - {community_type} - 暂无数据"
                self.chart_widget.update_chart([], [], [], title)
                self.region_info_label.setText(f"区域: {region_name} | 类型: {community_type}")
                self.price_info_label.setText("均价: 暂无数据")
                self.change_info_label.setText("涨跌: --")
                logger.info(f"{region_name}/{community_type} 暂无数据")

        except Exception as e:
            logger.error(f"加载图表失败: {e}")
            self.status_bar.showMessage(f"加载失败: {e}")

    def _load_region_summary(self, region_name: str):
        """加载某区域各类型汇总对比"""
        try:
            summary = get_region_summary(region_name, days=30)

            if summary:
                parts = []
                for item in summary:
                    t = item["type"]
                    p = item["avg_price"]
                    c = item["change_pct"]
                    if c > 0:
                        parts.append(f"🔴 {t}: {p:,.0f}元/㎡ (+{c:.1f}%)")
                    elif c < 0:
                        parts.append(f"🟢 {t}: {p:,.0f}元/㎡ ({c:.1f}%)")
                    else:
                        parts.append(f"⚪ {t}: {p:,.0f}元/㎡ (持平)")

                self.summary_label.setText(" | ".join(parts))
            else:
                self.summary_label.setText("各类型汇总: 暂无数据")

        except Exception as e:
            logger.error(f"加载汇总失败: {e}")
