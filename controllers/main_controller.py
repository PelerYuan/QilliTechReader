import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from models.continue_read_worker import ContinuousReadWorker
from models.gauge_model import GaugeModel
from models.serial_auto_detect import AutoDetectWorker
from models.serial_model import SerialModel
from views.main_window import MainWindow
from views.dialogs import *
from datetime import datetime


class MainController(QObject):
    """主控制器 - 协调Model和View"""

    def __init__(self):
        super().__init__()

        # 创建模型和视图
        self.gauge_model = GaugeModel()
        self.serial_model = SerialModel()
        self.view = MainWindow()

        # 连接信号和槽
        self.setup_connections()

        # 初始化
        self.initialize()

        # 连续读取相关
        self.read_thread = None
        self.read_worker = None

    def setup_connections(self):
        """设置信号连接"""
        # 视图 -> 控制器
        self.view.connectRequested.connect(self.handle_connect)
        self.view.disconnectRequested.connect(self.handle_disconnect)
        self.view.autoDetectRequested.connect(self.handle_auto_detect)
        self.view.singleReadRequested.connect(self.handle_single_read)
        self.view.continuousReadRequested.connect(self.handle_continuous_read)
        self.view.stopReadRequested.connect(self.handle_stop_read)
        self.view.zeroRequested.connect(self.handle_zero)

        # 模型 -> 视图
        self.gauge_model.dataChanged.connect(self.handle_data_changed)
        self.gauge_model.statusChanged.connect(self.view.update_status)
        self.gauge_model.connectionChanged.connect(self.view.set_connection_status)
        self.gauge_model.errorOccurred.connect(self.handle_error)

        # 串口模型 -> 控制器
        self.serial_model.errorOccurred.connect(self.handle_serial_error)
        self.serial_model.connectionStatusChanged.connect(self.handle_connection_status_changed)
        self.serial_model.dataReceived.connect(self.handle_data_received)

    def initialize(self):
        """初始化设置"""
        # 扫描可用串口
        ports = self.serial_model.get_available_ports()
        self.view.update_port_list(ports)

        # 显示初始状态信息
        interval_info = self.view.get_interval_info_text()
        self.view.update_status(f"就绪 - 请选择串口并连接设备 | {interval_info}")

    # ========== 事件处理方法 ==========
    def handle_connect(self, port, baudrate):
        """处理连接请求"""
        print(f"Controller: 处理连接请求 {port} @ {baudrate}")

        try:
            # 显示连接状态
            self.view.update_status("正在连接设备...")
            self.view.connect_pushButton.setEnabled(False)
            self.view.connect_pushButton.setText("连接中...")

            # 尝试连接
            success = self.serial_model.connect(port, baudrate)

            if success:
                # 连接成功
                self.gauge_model.is_connected = True
                self.gauge_model._port = port
                self.gauge_model._baudrate = baudrate

                # 更新状态栏显示连接信息
                status_msg = f"已连接 - {port} @ {baudrate} bps"
                self.view.update_status(status_msg)

                print(f"连接成功: {port} @ {baudrate}")

            else:
                # 连接失败，但错误信息通过信号处理
                self.view.connect_pushButton.setEnabled(True)
                self.view.connect_pushButton.setText("连接")

        except Exception as e:
            # 处理意外错误
            self.view.connect_pushButton.setEnabled(True)
            self.view.connect_pushButton.setText("连接")
            self.handle_connection_error(str(e), port, baudrate)

    def handle_disconnect(self):
        """处理断开请求"""
        print("Controller: 处理断开请求")
        # 先停止读取
        if self.gauge_model.is_reading:
            self.handle_stop_read()
        # 再断开连接
        self.serial_model.disconnect()
        self.gauge_model.is_connected = False
        self.view.update_status("已断开连接")

    def handle_auto_detect(self):
        """处理自动检测请求"""
        print("Controller: 处理自动检测请求")

        # 获取当前选择的串口
        current_port = self.view.port_comboBox.currentText()
        if current_port == "请选择串口" or not current_port:
            QMessageBox.warning(self.view, "警告", "请先选择要检测的串口！")
            return

        # 获取当前波特率
        current_baudrate = int(self.view.baudrate_comboBox.currentText())

        # 显示检测进度
        self.view.update_status("正在自动检测波特率...")
        self.view.auto_detect_pushButton.setEnabled(False)
        self.view.auto_detect_pushButton.setText("检测中...")

        # 创建检测线程
        self.detect_thread = QThread()
        self.detect_worker = AutoDetectWorker(current_port)
        self.detect_worker.moveToThread(self.detect_thread)

        # 连接信号
        self.detect_thread.started.connect(self.detect_worker.run)
        self.detect_worker.finished.connect(self.on_auto_detect_finished)
        self.detect_worker.finished.connect(self.detect_thread.quit)
        self.detect_worker.finished.connect(self.detect_worker.deleteLater)
        self.detect_thread.finished.connect(self.detect_thread.deleteLater)

        # 启动检测
        self.detect_thread.start()

    def on_auto_detect_finished(self, detected_baudrate):
        """自动检测完成回调"""
        # 恢复按钮状态
        self.view.auto_detect_pushButton.setEnabled(True)
        self.view.auto_detect_pushButton.setText("自动检测")

        current_baudrate = int(self.view.baudrate_comboBox.currentText())

        # 显示检测结果对话框
        dialog = AutoDetectDialog(current_baudrate, detected_baudrate, self.view)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_baudrate:
            # 用户选择了波特率
            self.view.baudrate_comboBox.setCurrentText(str(dialog.selected_baudrate))
            if detected_baudrate:
                self.view.update_status(f"自动检测完成，波特率已设置为 {dialog.selected_baudrate}")
            else:
                self.view.update_status("使用当前波特率设置")
        else:
            self.view.update_status("自动检测已取消")

    def handle_single_read(self):
        """处理单次读取请求"""
        print("Controller: 处理单次读取请求")

        if not self.gauge_model.is_connected:
            QMessageBox.warning(self.view, "警告", "请先连接设备！")
            return

        try:
            self.view.update_status("正在读取数据...")

            # 读取数据
            value = self.serial_model.read_value()

            # 添加调试信息
            print(f"Debug: 读取到的原始值: {value}")

            if value is not None:
                # 更新模型
                self.gauge_model.current_value = value

                # 获取连接信息
                conn_info = self.gauge_model.get_current_connection_info()

                # 添加调试信息
                print(f"Debug: 准备显示对话框，值: {value}, 端口: {conn_info['port']}")

                # 显示读取结果对话框
                dialog = SingleReadDialog(
                    value,
                    conn_info['port'],
                    conn_info['baudrate'],
                    self.view
                )
                dialog.exec_()

                self.view.update_status("单次读取完成")
            else:
                print("Debug: 读取值为None")  # 添加调试
                QMessageBox.warning(self.view, "读取失败", "无法读取设备数据，请检查连接。")
                self.view.update_status("单次读取失败")

        except Exception as e:
            print(f"Debug: 异常信息: {e}")  # 添加调试
            QMessageBox.critical(self.view, "读取错误", f"读取过程中发生错误：{str(e)}")
            self.view.update_status(f"读取错误: {str(e)}")

    def handle_continuous_read(self, interval):
        """处理连续读取请求"""
        print(f"Controller: 处理连续读取请求，间隔 {interval}秒")

        if not self.gauge_model.is_connected:
            QMessageBox.warning(self.view, "警告", "请先连接设备！")
            return

        try:
            # 创建读取线程
            self.read_thread = QThread()
            self.read_worker = ContinuousReadWorker(self.serial_model, interval)
            self.read_worker.moveToThread(self.read_thread)

            # 连接信号
            self.read_thread.started.connect(self.read_worker.start_reading)
            self.read_worker.dataRead.connect(self.handle_continuous_data)
            self.read_worker.errorOccurred.connect(self.handle_continuous_read_error)
            self.read_worker.finished.connect(self.read_thread.quit)
            self.read_worker.finished.connect(self.read_worker.deleteLater)
            self.read_thread.finished.connect(self.read_thread.deleteLater)

            # 启动线程
            self.read_thread.start()

            # 更新状态
            self.gauge_model.is_reading = True
            self.view.set_continuous_read_status(True)
            self.view.update_status(f"正在连续读取 (间隔: {interval}s)")

        except Exception as e:
            QMessageBox.critical(self.view, "启动错误", f"无法启动连续读取：{str(e)}")
            self.view.update_status(f"启动错误: {str(e)}")

    def handle_stop_read(self):
        """处理停止读取请求"""
        print("Controller: 处理停止读取请求")

        if self.read_worker:
            self.read_worker.stop_reading()

        self.gauge_model.is_reading = False
        self.view.set_continuous_read_status(False)
        self.view.update_status("已停止读取")

    def handle_continuous_data(self, value, timestamp):
        """处理连续读取的数据"""
        # 更新模型
        self.gauge_model.current_value = value

        # 添加到表格
        self.view.add_data_to_table(timestamp, value)

    def handle_continuous_read_error(self, error_msg):
        """处理连续读取错误"""
        print(f"连续读取错误: {error_msg}")

        # 停止读取
        self.handle_stop_read()

        # 显示错误
        QMessageBox.warning(self.view, "读取错误", f"连续读取过程中发生错误：{error_msg}")
        self.view.update_status(f"读取错误: {error_msg}")

    def handle_zero(self):
        """处理清零请求"""
        print("Controller: 处理清零请求")

        if not self.gauge_model.is_connected:
            QMessageBox.warning(self.view, "警告", "请先连接设备！")
            return

        # 如果正在连续读取，先停止
        if self.gauge_model.is_reading:
            reply = QMessageBox.question(
                self.view,
                "确认操作",
                "当前正在进行连续读取，清零操作将停止读取。是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            self.handle_stop_read()

        # 获取当前数据条数
        data_count = self.view.get_data_count()

        # 显示确认对话框
        dialog = ZeroConfirmDialog(data_count, self.view)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            try:
                self.view.update_status("正在执行清零操作...")

                # 执行设备清零
                success = self.serial_model.zero_device()

                if success:
                    # 清空表格数据
                    self.view.clear_data_table()

                    # 更新当前值为0
                    self.gauge_model.current_value = 0.0

                    self.view.update_status("清零操作完成")
                    QMessageBox.information(self.view, "操作成功", "设备清零和数据清空操作已完成。")
                else:
                    self.view.update_status("设备清零失败")
                    QMessageBox.warning(self.view, "操作失败", "设备清零操作失败，请检查设备连接。")

            except Exception as e:
                self.view.update_status(f"清零错误: {str(e)}")
                QMessageBox.critical(self.view, "清零错误", f"清零过程中发生错误：{str(e)}")
        else:
            self.view.update_status("清零操作已取消")

    def handle_data_changed(self, value):
        """处理数据变化"""
        # 可以在这里添加数据到表格
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.view.add_data_to_table(timestamp, value)

    def handle_error(self, error_msg):
        """处理错误"""
        print(f"Controller: 处理错误 - {error_msg}")
        QMessageBox.warning(self.view, "错误", error_msg)
        self.view.update_status(f"错误: {error_msg}")

    def handle_serial_error(self, error_msg):
        """处理串口错误"""
        port = self.view.port_comboBox.currentText()
        baudrate = int(self.view.baudrate_comboBox.currentText())
        self.handle_connection_error(error_msg, port, baudrate)

    def handle_connection_error(self, error_msg, port, baudrate):
        """处理连接错误"""
        print(f"连接错误: {error_msg}")

        # 显示连接错误对话框
        dialog = ConnectionErrorDialog(error_msg, port, baudrate, self.view)
        result = dialog.exec_()

        if result == 2:  # 用户选择自动检测
            self.handle_auto_detect()

        # 更新状态
        self.view.update_status(f"连接失败: {error_msg}")

    def handle_connection_status_changed(self, connected):
        """处理连接状态变化"""
        if connected:
            # 连接成功，恢复按钮状态
            self.view.connect_pushButton.setEnabled(True)
            self.view.connect_pushButton.setText("断开")
        else:
            # 连接断开
            self.gauge_model.is_connected = False
            self.view.connect_pushButton.setEnabled(True)
            self.view.connect_pushButton.setText("连接")

    def handle_data_received(self, value):
        """处理接收到的数据"""
        # 更新模型中的当前值
        self.gauge_model.current_value = value

    def show(self):
        """显示主窗口"""
        self.view.show()