"""
张家港房价App - K线图组件
使用 PyQt6 + QWebEngineView + ECharts 显示K线图
支持按小区类型(别墅/洋房/拆迁房/老小区/高层)分别显示
"""

import json
from typing import List, Dict, Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from src.utils.logger import get_logger

logger = get_logger("chart")


def _build_echart_html(title: str, dates: List[str],
                       ohlcs: List[list], volumes: List[int],
                       unit: str = "元/㎡") -> str:
    """
    生成完整的 ECharts HTML 页面。
    纯字符串拼接，不使用 .format() 避免与 JS 花括号冲突。

    参数:
        unit: 价格单位，如 '元/㎡' 或 '元/月'
    """
    dates_json = json.dumps(dates, ensure_ascii=False)
    ohlcs_json = json.dumps(ohlcs)
    volumes_json = json.dumps(volumes)

    # 计算 dataZoom 起始位置（显示最近30天）
    total = len(dates)
    zoom_start = max(0, ((total - 30) / total) * 100) if total > 30 else 0

    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#1a1a2e; overflow:hidden; }
  #chart { width:100vw; height:100vh; }
</style>
</head><body>
<div id="chart"></div>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<script>
var chart = echarts.init(document.getElementById('chart'));

var dates = """ + dates_json + """;
var ohlcs = """ + ohlcs_json + """;
var volumes = """ + volumes_json + """;

var option = {
  backgroundColor: '#1a1a2e',
  title: {
    text: '""" + title + """',
    textStyle: { color: '#e0e0e0', fontSize: 16 },
    left: 'center'
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
    backgroundColor: 'rgba(20,20,50,0.95)',
    borderColor: '#666',
    textStyle: { color: '#fff', fontSize: 12 },
    formatter: function(params) {
      var res = '<b>' + params[0].axisValue + '</b><br/>';
      params.forEach(function(p) {
        if (p.seriesType === 'candlestick') {
          var d = p.data;
          var isUp = d[2] >= d[1];
          var clr = isUp ? '#FF4444' : '#00CC66';
          res += '<span style="color:' + clr + '">● K线</span><br/>';
          res += '&nbsp;&nbsp;开盘: ' + d[1].toLocaleString() + ' """ + unit + """<br/>';
          res += '&nbsp;&nbsp;收盘: ' + d[2].toLocaleString() + ' """ + unit + """<br/>';
          res += '&nbsp;&nbsp;最低: ' + d[3].toLocaleString() + ' """ + unit + """<br/>';
          res += '&nbsp;&nbsp;最高: ' + d[4].toLocaleString() + ' """ + unit + """<br/>';
        } else if (p.seriesType === 'bar') {
          res += '<span style="color:#888">● 成交量: ' + p.data + ' 套</span><br/>';
        }
      });
      return res;
    }
  },
  legend: {
    data: ['K线', '成交量'],
    textStyle: { color: '#aaa' },
    top: 30
  },
  grid: [
    { left: '10%', right: '8%', top: '15%', height: '55%' },
    { left: '10%', right: '8%', top: '75%', height: '12%' }
  ],
  xAxis: [
    {
      type: 'category',
      data: dates,
      gridIndex: 0,
      axisLine: { lineStyle: { color: '#555' } },
      axisLabel: { color: '#aaa', fontSize: 10 },
      splitLine: { show: false }
    },
    {
      type: 'category',
      data: dates,
      gridIndex: 1,
      axisLine: { lineStyle: { color: '#555' } },
      axisLabel: { show: false },
      splitLine: { show: false }
    }
  ],
  yAxis: [
    {
      type: 'value',
      name: '""" + unit + """',
      nameTextStyle: { color: '#aaa' },
      gridIndex: 0,
      axisLine: { lineStyle: { color: '#555' } },
      axisLabel: {
        color: '#aaa',
        formatter: function(v) { return (v/10000).toFixed(1) + '万'; }
      },
      splitLine: { lineStyle: { color: '#2a2a4a' } },
      scale: true
    },
    {
      type: 'value',
      name: '套',
      gridIndex: 1,
      axisLine: { lineStyle: { color: '#555' } },
      axisLabel: { color: '#aaa', fontSize: 9 },
      splitLine: { show: false }
    }
  ],
  dataZoom: [
    {
      type: 'inside',
      xAxisIndex: [0, 1],
      start: """ + str(zoom_start) + """,
      end: 100
    },
    {
      type: 'slider',
      xAxisIndex: [0, 1],
      start: """ + str(zoom_start) + """,
      end: 100,
      top: '92%',
      textStyle: { color: '#aaa' },
      borderColor: '#444',
      fillerColor: 'rgba(100,100,200,0.2)',
      handleStyle: { color: '#4CAF50' }
    }
  ],
  series: [
    {
      name: 'K线',
      type: 'candlestick',
      data: ohlcs,
      xAxisIndex: 0,
      yAxisIndex: 0,
      itemStyle: {
        color: '#FF4444',
        color0: '#00CC66',
        borderColor: '#FF4444',
        borderColor0: '#00CC66'
      }
    },
    {
      name: '成交量',
      type: 'bar',
      data: volumes,
      xAxisIndex: 1,
      yAxisIndex: 1,
      itemStyle: { color: 'rgba(100,100,200,0.5)' }
    }
  ]
};

chart.setOption(option);

window.addEventListener('resize', function() { chart.resize(); });

function updateData(d, o, v) {
  chart.setOption({
    xAxis: [{ data: d }, { data: d }],
    series: [{ data: o }, { data: v }]
  });
}

window.__chart_ready = true;
</script></body></html>"""

    return html


class ChartWidget(QWidget):
    """
    K线图组件 - 封装了 ECharts 图表的显示和更新。
    支持显示 K线（蜡烛图）+ 成交量柱状图。
    """

    chart_loaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)
        self.layout.addWidget(self.progress_bar)

        # Web视图
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

        self._chart_ready = False
        self._pending_data = None  # 待显示的数据（如果图表还没准备好）

        # 初始化
        self._init_chart()

    def _init_chart(self):
        """初始化空白K线图"""
        html = _build_echart_html("加载中...", [], [], [], unit="元/㎡")
        self.web_view.setHtml(html)
        self.web_view.loadFinished.connect(self._on_load_finished)

    @pyqtSlot(bool)
    def _on_load_finished(self, ok: bool):
        """页面加载完成"""
        if ok:
            self._chart_ready = True
            self.progress_bar.hide()
            self.chart_loaded.emit()
            logger.info("图表初始化完成")

            # 如果有待显示的数据，立即显示
            if self._pending_data:
                self.update_chart(*self._pending_data)
                self._pending_data = None
        else:
            logger.error("图表加载失败")
            self.progress_bar.hide()

    def update_chart(self, dates: List[str], ohlcs: List[list],
                     volumes: List[int], title: str, unit: str = "元/㎡"):
        """
        更新K线图数据。

        参数:
            dates: 日期列表
            ohlcs: K线数据 [open, close, low, high]
            volumes: 成交量列表
            title: 图表标题
            unit: 价格单位（元/㎡ 或 元/月）
        """
        if not dates or not ohlcs:
            logger.warning("没有数据可用于更新图表")
            # 显示"暂无数据"提示
            html = _build_echart_html(title + " — 暂无数据", [], [], [], unit=unit)
            self.web_view.setHtml(html)
            return

        if not self._chart_ready:
            # 等待加载完成后再显示
            self._pending_data = (dates, ohlcs, volumes, title, unit)
            # 直接重新加载HTML（此时可能页面还没加载完，但setHtml会覆盖）
            html = _build_echart_html(title, dates, ohlcs, volumes, unit=unit)
            self.web_view.setHtml(html)
            return

        # 通过 JS 更新（更流畅）
        js_code = ("updateData("
                   + json.dumps(dates, ensure_ascii=False) + ", "
                   + json.dumps(ohlcs) + ", "
                   + json.dumps(volumes) + ");")
        self.web_view.page().runJavaScript(js_code)
        logger.debug(f"图表已更新: {len(dates)} 条, 标题={title}")
