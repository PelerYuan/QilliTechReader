import sys
from datetime import datetime, timedelta
from collections import deque
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg


class GaugeChartWidget(QWidget):
    """千分表数据动态折线图组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 数据存储 - 使用双端队列提高性能
        self.max_points = 1000  # 最大显示点数
        self.time_data = deque(maxlen=self.max_points)
        self.value_data = deque(maxlen=self.max_points)

        # 设置界面
        self.setup_ui()

        # 初始化图表
        self.setup_chart()

        # 自动缩放标志
        self.auto_scale_enabled = True

        # 时间轴显示范围（秒）
        self.time_range = 60  # 默认显示最近60秒

    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 控制面板
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

        # 图表区域
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

        # 状态标签
        self.status_label = QLabel("等待数据...")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

    def create_control_panel(self):
        """创建控制面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)

        layout = QHBoxLayout(panel)

        # 图表控制组
        chart_group = QGroupBox("图表控制")
        chart_layout = QHBoxLayout(chart_group)

        # 自动缩放开关
        self.auto_scale_checkbox = QCheckBox("自动缩放")
        self.auto_scale_checkbox.setChecked(True)
        self.auto_scale_checkbox.toggled.connect(self.toggle_auto_scale)
        chart_layout.addWidget(self.auto_scale_checkbox)

        # 清空数据按钮
        self.clear_button = QPushButton("清空图表")
        self.clear_button.clicked.connect(self.clear_chart)
        self.clear_button.setMaximumWidth(80)
        chart_layout.addWidget(self.clear_button)

        # 时间范围设置组
        time_group = QGroupBox("时间范围")
        time_layout = QHBoxLayout(time_group)

        time_layout.addWidget(QLabel("显示:"))

        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems([
            "30秒", "1分钟", "2分钟", "5分钟", "10分钟", "全部"
        ])
        self.time_range_combo.setCurrentText("1分钟")
        self.time_range_combo.currentTextChanged.connect(self.change_time_range)
        time_layout.addWidget(self.time_range_combo)

        # 数据统计组
        stats_group = QGroupBox("数据统计")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("点数: 0 | 最新: -- | 范围: --")
        self.stats_label.setStyleSheet("font-size: 20px; color: #555;")
        stats_layout.addWidget(self.stats_label)

        # 布局
        layout.addWidget(chart_group)
        layout.addWidget(time_group)
        layout.addWidget(stats_group)
        layout.addStretch()

        return panel

    def setup_chart(self):
        """设置图表"""
        # 配置图表外观
        self.plot_widget.setBackground('white')
        self.plot_widget.setLabel('left', '位移', units='mm')
        self.plot_widget.setLabel('bottom', '时间')
        self.plot_widget.setTitle('千分表实时数据', color='#333', size='12pt')

        # 启用网格
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # 设置坐标轴
        self.setup_axes()

        # 隐藏横轴刻度标签
        bottom_axis = self.plot_widget.getAxis('bottom')
        bottom_axis.setTicks([])  # 清空刻度标签

        # 创建曲线
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#2E86AB', width=2),
            symbol='o',
            symbolSize=4,
            symbolBrush='#2E86AB',
            name='位移数据'
        )

        # 添加零线参考
        self.zero_line = pg.InfiniteLine(
            pos=0,
            angle=0,
            pen=pg.mkPen('red', width=1, style=Qt.DashLine),
            label='零位'
        )
        self.plot_widget.addItem(self.zero_line)

        # 配置鼠标交互
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.enableAutoRange()

    def setup_axes(self):
        """设置坐标轴"""
        # 配置时间轴
        axis_x = self.plot_widget.getAxis('bottom')
        axis_x.setStyle(tickFont=QFont("Arial", 9))
        # 隐藏横轴数值
        axis_x.setStyle(showValues=False)

        # 配置数值轴
        axis_y = self.plot_widget.getAxis('left')
        axis_y.setStyle(tickFont=QFont("Arial", 9))

        # 自定义时间轴标签格式
        self.setup_time_axis()

    def setup_time_axis(self):
        """设置时间轴格式"""
        axis = self.plot_widget.getAxis('bottom')

        # 隐藏时间轴标签，只保留轴线和网格
        axis.setTicks([])  # 清空所有刻度标签
        axis.setStyle(showValues=False)  # 隐藏数值显示

    def add_data_point(self, timestamp, value):
        """添加数据点"""
        # 转换时间戳
        if isinstance(timestamp, str):
            # 如果是字符串格式 "HH:MM:SS.fff"
            try:
                today = datetime.now().date()
                time_part = datetime.strptime(timestamp, "%H:%M:%S.%f").time()
                dt = datetime.combine(today, time_part)
                timestamp = dt.timestamp()
            except ValueError:
                # 如果解析失败，使用当前时间
                timestamp = datetime.now().timestamp()
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.timestamp()

        # 添加数据
        self.time_data.append(timestamp)
        self.value_data.append(value)

        # 更新图表
        self.update_chart()

        # 更新状态
        self.update_status()

    def update_chart(self):
        """更新图表显示"""
        if len(self.time_data) == 0:
            return

        # 获取要显示的数据
        time_array, value_array = self.get_display_data()

        if len(time_array) == 0:
            return

        # 更新曲线数据
        self.curve.setData(time_array, value_array)

        # 自动缩放
        if self.auto_scale_enabled:
            self.auto_scale()

    def get_display_data(self):
        """获取要显示的数据"""
        if len(self.time_data) == 0:
            return [], []

        time_list = list(self.time_data)
        value_list = list(self.value_data)

        # 根据时间范围过滤数据
        if self.time_range_combo.currentText() != "全部":
            current_time = time_list[-1]
            time_window = self.get_time_window()

            # 过滤在时间窗口内的数据
            filtered_time = []
            filtered_value = []

            for i, t in enumerate(time_list):
                if current_time - t <= time_window:
                    filtered_time.append(t)
                    filtered_value.append(value_list[i])

            return filtered_time, filtered_value
        else:
            return time_list, value_list

    def get_time_window(self):
        """获取时间窗口大小（秒）"""
        text = self.time_range_combo.currentText()
        if text == "30秒":
            return 30
        elif text == "1分钟":
            return 60
        elif text == "2分钟":
            return 120
        elif text == "5分钟":
            return 300
        elif text == "10分钟":
            return 600
        else:
            return float('inf')  # 全部

    def auto_scale(self):
        """自动缩放"""
        if len(self.value_data) == 0:
            return

        time_array, value_array = self.get_display_data()

        if len(value_array) == 0:
            return

        # Y轴自动缩放（添加5%边距）
        min_val = min(value_array)
        max_val = max(value_array)

        if min_val == max_val:
            # 如果所有值相同，设置合理的范围
            center = min_val
            range_val = max(abs(center) * 0.1, 0.1)  # 至少0.1mm范围
            min_val = center - range_val
            max_val = center + range_val
        else:
            # 添加5%的边距
            range_val = max_val - min_val
            margin = range_val * 0.05
            min_val -= margin
            max_val += margin

        self.plot_widget.setYRange(min_val, max_val, padding=0)

        # X轴自动缩放
        if len(time_array) > 1:
            self.plot_widget.setXRange(time_array[0], time_array[-1], padding=0.02)

    def toggle_auto_scale(self, enabled):
        """切换自动缩放"""
        self.auto_scale_enabled = enabled
        if enabled:
            self.auto_scale()

    def change_time_range(self, text):
        """改变时间范围"""
        self.update_chart()

    def clear_chart(self):
        """清空图表"""
        self.time_data.clear()
        self.value_data.clear()
        self.curve.setData([], [])
        self.update_status()

    def update_status(self):
        """更新状态信息"""
        count = len(self.value_data)

        if count == 0:
            self.status_label.setText("等待数据...")
            self.stats_label.setText("点数: 0 | 最新: -- | 范围: --")
        else:
            # 获取最新值
            latest = self.value_data[-1]

            # 计算范围
            values = list(self.value_data)
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val

            # 更新状态
            self.status_label.setText(f"已接收 {count} 个数据点")
            self.stats_label.setText(
                f"点数: {count} | 最新: {latest:+.4f}mm | "
                f"范围: {min_val:+.4f} ~ {max_val:+.4f}mm (±{range_val:.4f})"
            )

    def get_chart_data(self):
        """获取图表数据（用于导出等）"""
        return {
            'time': list(self.time_data),
            'value': list(self.value_data),
            'count': len(self.value_data)
        }

    def set_max_points(self, max_points):
        """设置最大数据点数"""
        self.max_points = max_points
        # 重新创建队列
        old_time = list(self.time_data)
        old_value = list(self.value_data)

        self.time_data = deque(old_time[-max_points:], maxlen=max_points)
        self.value_data = deque(old_value[-max_points:], maxlen=max_points)

        self.update_chart()


class ChartTestWindow(QMainWindow):
    """图表测试窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("千分表图表测试")
        self.setGeometry(100, 100, 800, 600)

        # 创建图表组件
        self.chart = GaugeChartWidget()
        self.setCentralWidget(self.chart)

        # 创建测试定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.add_test_data)

        # 添加测试按钮
        self.create_test_toolbar()

        # 测试数据
        self.test_counter = 0

    def create_test_toolbar(self):
        """创建测试工具栏"""
        toolbar = self.addToolBar("测试")

        start_action = QAction("开始测试", self)
        start_action.triggered.connect(self.start_test)
        toolbar.addAction(start_action)

        stop_action = QAction("停止测试", self)
        stop_action.triggered.connect(self.stop_test)
        toolbar.addAction(stop_action)

        clear_action = QAction("清空", self)
        clear_action.triggered.connect(self.chart.clear_chart)
        toolbar.addAction(clear_action)

    def start_test(self):
        """开始测试"""
        self.timer.start(200)  # 每200ms添加一个数据点

    def stop_test(self):
        """停止测试"""
        self.timer.stop()

    def add_test_data(self):
        """添加测试数据"""
        import math
        import random

        # 生成模拟数据
        t = self.test_counter * 0.2
        base_value = 2 * math.sin(t * 0.1) + 0.5 * math.cos(t * 0.3)
        noise = random.uniform(-0.1, 0.1)
        value = base_value + noise

        # 添加到图表
        timestamp = datetime.now()
        self.chart.add_data_point(timestamp, value)

        self.test_counter += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 测试窗口
    window = ChartTestWindow()
    window.show()

    sys.exit(app.exec_())