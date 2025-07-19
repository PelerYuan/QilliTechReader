import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from models.interval_calculator import IntervalCalculator
# 导入你的UI文件
from .ui.MainWindow import Ui_MainWindow
from .dialogs import *
# 导入图表组件
from .chart_widget import GaugeChartWidget


class MainWindow(QMainWindow, Ui_MainWindow):
    """主窗口视图 - 继承你的UI设计"""

    # 定义视图信号
    connectRequested = pyqtSignal(str, int)  # 连接请求 (port, baudrate)
    disconnectRequested = pyqtSignal()  # 断开请求
    autoDetectRequested = pyqtSignal()  # 自动检测请求
    singleReadRequested = pyqtSignal()  # 单次读取请求
    continuousReadRequested = pyqtSignal(float)  # 连续读取请求 (interval)
    stopReadRequested = pyqtSignal()  # 停止读取请求
    zeroRequested = pyqtSignal()  # 清零请求

    def __init__(self):
        super().__init__()
        # 设置UI（来自你的.ui文件）
        self.setupUi(self)

        # 修正中文显示问题
        self.fix_chinese_labels()

        # 设置图表组件
        self.setup_chart()

        # 设置连接和初始值
        self.setup_connections()
        self.setup_initial_values()

        # 初始化状态
        self._is_connected = False
        self._is_reading = False

    def fix_chinese_labels(self):
        """修正中文显示问题"""
        self.setWindowTitle("千分表数据读取器")
        self.groupBox.setTitle("通信设置")
        self.groupBox_2.setTitle("数据操作")

        # 修正标签文本
        self.label.setText("串口:")
        self.label_2.setText("波特率:")
        self.label_3.setText("读取间隔(s):")

        # 修正按钮文本
        self.auto_detect_pushButton.setText("自动检测")
        self.connect_pushButton.setText("连接")
        self.read_once_pushButton.setText("单次读取")
        self.read_serious_pushButton.setText("开始连续读取")
        self.clear_pushButton.setText("清零")

        # 修正标签页标题
        self.tabWidget.setTabText(0, "图表")
        self.tabWidget.setTabText(1, "数据")

        # 修正菜单
        if hasattr(self, 'menu'):
            self.menu.setTitle("文件")
        if hasattr(self, 'menu_2'):
            self.menu_2.setTitle("导出为...")
        if hasattr(self, 'action'):
            self.action.setText("新建")
        if hasattr(self, 'action_2'):
            self.action_2.setText("退出")

    def setup_chart(self):
        """设置图表组件"""
        # 创建图表组件
        self.chart_widget = GaugeChartWidget()

        # 将图表组件添加到图表标签页
        # 清空原有的布局内容
        if self.verticalLayout_2.count() > 0:
            for i in reversed(range(self.verticalLayout_2.count())):
                self.verticalLayout_2.itemAt(i).widget().setParent(None)

        # 添加图表组件
        self.verticalLayout_2.addWidget(self.chart_widget)

    def setup_connections(self):
        """连接信号和槽"""
        # 连接按钮信号
        self.connect_pushButton.clicked.connect(self.on_connect_clicked)
        self.auto_detect_pushButton.clicked.connect(self.autoDetectRequested.emit)
        self.read_once_pushButton.clicked.connect(self.singleReadRequested.emit)
        self.read_serious_pushButton.clicked.connect(self.on_continuous_read_clicked)
        self.clear_pushButton.clicked.connect(self.on_clear_clicked)

        # 连接读取间隔变化信号
        self.read_interval_doubleSpinBox.valueChanged.connect(self.on_interval_changed)

        # 连接菜单动作（如果存在）
        if hasattr(self, 'action_2'):  # 退出
            self.action_2.triggered.connect(self.close)

    def setup_initial_values(self):
        """设置初始值"""
        # 波特率选项
        baudrates = ["9600", "19200", "38400", "57600", "115200"]
        self.baudrate_comboBox.addItems(baudrates)
        self.baudrate_comboBox.setCurrentText("9600")

        # 设置读取间隔范围和默认值
        self.read_interval_doubleSpinBox.setRange(0.001, 10.0)  # 允许更小的值用于验证
        self.read_interval_doubleSpinBox.setValue(0.2)
        self.read_interval_doubleSpinBox.setSingleStep(0.01)
        self.read_interval_doubleSpinBox.setDecimals(3)

        # 串口选项（初始为空，由控制器填充）
        self.port_comboBox.addItems(["请选择串口"])

        # 设置表格列标题
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["时间", "数值(mm)"])

        # 初始状态设置
        self.set_operation_buttons_enabled(False)

        # 初始间隔验证
        self.validate_initial_interval()

    def on_connect_clicked(self):
        """连接按钮点击处理"""
        if not self._is_connected:
            port = self.port_comboBox.currentText()
            if port == "请选择串口":
                QMessageBox.warning(self, "警告", "请先选择串口！")
                return
            baudrate = int(self.baudrate_comboBox.currentText())
            self.connectRequested.emit(port, baudrate)
        else:
            self.disconnectRequested.emit()

    def on_continuous_read_clicked(self):
        """连续读取按钮点击处理"""
        if not self._is_reading:
            interval = self.read_interval_doubleSpinBox.value()
            self.continuousReadRequested.emit(interval)
        else:
            self.stopReadRequested.emit()

    def on_clear_clicked(self):
        """清零按钮点击处理"""
        # 发出清零请求信号
        self.zeroRequested.emit()

    def on_interval_changed(self, value):
        """读取间隔改变处理"""
        current_baudrate = int(self.baudrate_comboBox.currentText())

        # 检查间隔是否有效
        if not IntervalCalculator.is_interval_valid(value, current_baudrate):
            # 间隔过小，显示警告
            min_interval = IntervalCalculator.calculate_min_interval(current_baudrate)
            suggested_baudrate = IntervalCalculator.suggest_baudrate(value)

            # 显示警告对话框
            dialog = IntervalWarningDialog(
                value, current_baudrate, min_interval, suggested_baudrate, self
            )
            result = dialog.exec_()

            if result == QDialog.Accepted:
                if dialog.user_choice == "baudrate":
                    # 用户选择使用建议波特率
                    self.baudrate_comboBox.setCurrentText(str(suggested_baudrate))
                    self.update_status(f"波特率已调整为 {suggested_baudrate} bps")
                elif dialog.user_choice == "interval":
                    # 用户选择调整间隔
                    self.read_interval_doubleSpinBox.setValue(min_interval)
                    self.update_status(f"读取间隔已调整为 {min_interval:.3f} 秒")
            else:
                # 用户取消，恢复到有效值
                min_interval = IntervalCalculator.calculate_min_interval(current_baudrate)
                self.read_interval_doubleSpinBox.setValue(min_interval)
                self.update_status("已恢复到最小有效间隔")

    # ========== 供控制器调用的方法 ==========
    def update_port_list(self, ports):
        """更新串口列表"""
        current_port = self.port_comboBox.currentText()
        self.port_comboBox.clear()
        self.port_comboBox.addItems(ports)

        # 尝试恢复之前选择的串口
        if current_port in ports:
            self.port_comboBox.setCurrentText(current_port)

    def update_status(self, status):
        """更新状态栏"""
        self.statusbar.showMessage(status)

    def set_connection_status(self, connected):
        """设置连接状态"""
        self._is_connected = connected
        if connected:
            self.connect_pushButton.setText("断开")
            self.set_operation_buttons_enabled(True)
            # 连接后禁用通信设置
            self.port_comboBox.setEnabled(False)
            self.baudrate_comboBox.setEnabled(False)
            self.auto_detect_pushButton.setEnabled(False)
        else:
            self.connect_pushButton.setText("连接")
            self.set_operation_buttons_enabled(False)
            # 断开后启用通信设置
            self.port_comboBox.setEnabled(True)
            self.baudrate_comboBox.setEnabled(True)
            self.auto_detect_pushButton.setEnabled(True)
            # 重置读取状态
            self.set_continuous_read_status(False)

    def set_operation_buttons_enabled(self, enabled):
        """设置操作按钮可用状态"""
        self.read_once_pushButton.setEnabled(enabled)
        self.read_serious_pushButton.setEnabled(enabled)
        self.clear_pushButton.setEnabled(enabled)

    def set_continuous_read_status(self, reading):
        """设置连续读取状态"""
        self._is_reading = reading
        if reading:
            self.read_serious_pushButton.setText("停止读取")
            # 读取时禁用其他操作
            self.read_once_pushButton.setEnabled(False)
            self.clear_pushButton.setEnabled(False)
            self.read_interval_doubleSpinBox.setEnabled(False)
        else:
            self.read_serious_pushButton.setText("开始连续读取")
            # 恢复其他操作
            if self._is_connected:
                self.read_once_pushButton.setEnabled(True)
                self.clear_pushButton.setEnabled(True)
            self.read_interval_doubleSpinBox.setEnabled(True)

    def add_data_to_table(self, timestamp, value):
        """向数据表格添加数据"""
        row_count = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_count)

        self.tableWidget.setItem(row_count, 0, QTableWidgetItem(timestamp))
        self.tableWidget.setItem(row_count, 1, QTableWidgetItem(f"{value:+8.4f}"))

        # 自动滚动到最新数据
        self.tableWidget.scrollToBottom()

    def add_data_to_chart(self, timestamp, value):
        """向图表添加数据"""
        self.chart_widget.add_data_point(timestamp, value)

    def clear_data_table(self):
        """清空数据表格"""
        self.tableWidget.setRowCount(0)

    def clear_chart(self):
        """清空图表"""
        self.chart_widget.clear_chart()

    def clear_all_data(self):
        """清空所有数据（表格和图表）"""
        self.clear_data_table()
        self.clear_chart()

    def validate_initial_interval(self):
        """验证初始间隔设置"""
        # 在初始化时检查默认间隔是否合适
        current_interval = self.read_interval_doubleSpinBox.value()
        current_baudrate = int(self.baudrate_comboBox.currentText())

        if not IntervalCalculator.is_interval_valid(current_interval, current_baudrate):
            # 如果默认值不合适，设置为最小有效值
            min_interval = IntervalCalculator.calculate_min_interval(current_baudrate)
            self.read_interval_doubleSpinBox.setValue(min_interval)

    def get_interval_info_text(self):
        """获取当前间隔的信息文本"""
        current_interval = self.read_interval_doubleSpinBox.value()
        current_baudrate = int(self.baudrate_comboBox.currentText())
        min_interval = IntervalCalculator.calculate_min_interval(current_baudrate)
        max_frequency = 1.0 / min_interval

        return f"当前: {current_interval:.3f}s | 最小: {min_interval:.3f}s | 最大频率: {max_frequency:.1f}Hz"

    def get_data_count(self):
        """获取表格中的数据行数"""
        return self.tableWidget.rowCount()

    def get_chart_data_count(self):
        """获取图表中的数据点数"""
        return len(self.chart_widget.value_data)

    def export_chart_data(self):
        """导出图表数据"""
        return self.chart_widget.get_chart_data()

    def set_chart_max_points(self, max_points):
        """设置图表最大数据点数"""
        self.chart_widget.set_max_points(max_points)