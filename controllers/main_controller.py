import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from models.continue_read_worker import ContinuousReadWorker
from models.gauge_model import GaugeModel
from models.serial_auto_detect import AutoDetectWorker
from models.serial_model import SerialModel
from views.main_window import MainWindow
from models.gauge_reader import GaugeReader
from views.dialogs import *
from datetime import datetime

import os
import csv
from datetime import datetime

# 添加这些可选导入
try:
    import pandas as pd
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    import sqlite3
    ACCESS_AVAILABLE = True
except ImportError:
    ACCESS_AVAILABLE = False


class MainController(QObject):
    """主控制器 - 协调Model和View"""

    def __init__(self):
        super().__init__()

        # 创建模型和视图
        self.gauge_model = GaugeModel()
        self.serial_model = SerialModel()
        self.view = MainWindow()

        # 设置视图的控制器引用
        self.view.set_controller(self)

        # 连接信号和槽
        self.setup_connections()
        self.setup_menu_connections()

        # 初始化
        self.initialize()

        # 连续读取相关
        self.read_thread = None
        self.read_worker = None

        # 存储所有打开的窗口实例
        self.open_windows = []

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

            # ========== 修改1：在连接时禁用自动检测按钮 ==========
            self.view.auto_detect_pushButton.setEnabled(False)

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
                # 连接失败，恢复按钮状态
                self.view.connect_pushButton.setEnabled(True)
                self.view.connect_pushButton.setText("连接")
                # ========== 修改1：连接失败时恢复自动检测按钮 ==========
                self.view.auto_detect_pushButton.setEnabled(True)

        except Exception as e:
            # 处理意外错误，恢复按钮状态
            self.view.connect_pushButton.setEnabled(True)
            self.view.connect_pushButton.setText("连接")
            # ========== 修改1：出现异常时恢复自动检测按钮 ==========
            self.view.auto_detect_pushButton.setEnabled(True)
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

        # ========== 修改2：在自动检测时禁用连接按钮 ==========
        self.view.connect_pushButton.setEnabled(False)

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
        self.view.connect_pushButton.setEnabled(True)

        current_baudrate = int(self.view.baudrate_comboBox.currentText())

        # 显示检测结果对话框
        dialog = AutoDetectDialog(current_baudrate, detected_baudrate, self.view)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_baudrate:
            # 检查是否需要修改设备波特率
            if dialog.should_change_device_baudrate:
                self.change_device_baudrate(dialog.selected_baudrate, detected_baudrate)
            else:
                # 只更新界面波特率设置
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

            if value is not None:
                # 更新模型
                self.gauge_model.current_value = value

                # 添加到表格和图表
                # timestamp = datetime.now()
                # timestamp_str = timestamp.strftime("%H:%M:%S.%f")[:-3]
                #
                # self.view.add_data_to_table(timestamp_str, value)
                # self.view.add_data_to_chart(timestamp, value)

                # 获取连接信息
                conn_info = self.gauge_model.get_current_connection_info()

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
                QMessageBox.warning(self.view, "读取失败", "无法读取设备数据，请检查连接。")
                self.view.update_status("单次读取失败")

        except Exception as e:
            print(e)
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

        # 同时添加到表格和图表
        self.view.add_data_to_table(timestamp, value)

        # 为图表创建datetime对象
        try:
            # 解析时间戳字符串为datetime对象
            today = datetime.now().date()
            time_part = datetime.strptime(timestamp, "%H:%M:%S.%f").time()
            dt = datetime.combine(today, time_part)
            self.view.add_data_to_chart(dt, value)
        except ValueError:
            # 如果解析失败，使用当前时间
            self.view.add_data_to_chart(datetime.now(), value)

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

        # 获取当前数据条数（表格和图表）
        table_count = self.view.get_data_count()
        chart_count = self.view.get_chart_data_count()
        total_count = max(table_count, chart_count)

        # 显示确认对话框
        dialog = ZeroConfirmDialog(total_count, self.view)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            try:
                self.view.update_status("正在执行清零操作...")

                # 执行设备清零
                success = self.serial_model.zero_device()

                if success:
                    # 清空表格数据和图表
                    self.view.clear_all_data()

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
        # 这个方法现在主要用于其他可能的数据更新场景
        # 表格和图表的更新在具体的读取方法中处理
        pass

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
            # ========== 修改1：连接成功后，自动检测按钮保持禁用状态（因为已连接） ==========
            # 注意：这里不恢复自动检测按钮，因为已经连接，不需要再检测
        else:
            # 连接断开，恢复所有按钮状态
            self.gauge_model.is_connected = False
            self.view.connect_pushButton.setEnabled(True)
            self.view.connect_pushButton.setText("连接")
            # ========== 修改1：断开连接时恢复自动检测按钮 ==========
            self.view.auto_detect_pushButton.setEnabled(True)

    def handle_data_received(self, value):
        """处理接收到的数据"""
        # 更新模型中的当前值
        self.gauge_model.current_value = value

    def show(self):
        """显示主窗口"""
        self.view.show()

    def export_data(self):
        """导出数据（表格和图表）"""
        try:
            # 获取图表数据
            chart_data = self.view.export_chart_data()

            # 可以添加导出到文件的逻辑
            return {
                'table_rows': self.view.get_data_count(),
                'chart_points': chart_data['count'],
                'chart_data': chart_data
            }
        except Exception as e:
            print(f"导出数据时出错: {e}")
            return None

    def set_chart_preferences(self, max_points=1000):
        """设置图表偏好"""
        self.view.set_chart_max_points(max_points)

    def handle_new_window(self):
        """处理新建窗口请求"""
        try:
            new_controller = MainController()
            self.open_windows.append(new_controller)
            window_count = len(self.open_windows)
            new_controller.view.setWindowTitle(f"千分表数据读取器 - 窗口 {window_count}")
            new_controller.show()
            self.view.update_status(f"已打开新窗口 - 窗口 {window_count}")
        except Exception as e:
            QMessageBox.critical(self.view, "错误", f"无法创建新窗口：{str(e)}")

    def handle_exit(self):
        """处理退出请求"""
        # 直接停止所有操作，不询问确认
        if self.gauge_model.is_reading:
            self.handle_stop_read()

        if self.gauge_model.is_connected:
            self.handle_disconnect()

        # 关闭窗口
        self.view.close()
        return True

    def get_table_data(self):
        """获取表格数据的辅助方法"""
        table_data = []
        table = self.view.tableWidget
        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            table_data.append(row_data)
        return table_data

    def setup_menu_connections(self):
        """设置菜单信号连接"""
        if hasattr(self.view, 'action'):  # 新建
            self.view.action.triggered.connect(self.handle_new_window)

        if hasattr(self.view, 'action_2'):  # 退出
            self.view.action_2.triggered.connect(self.handle_exit)

        if hasattr(self.view, 'actionCSV'):
            self.view.actionCSV.triggered.connect(self.handle_export_csv)

        if hasattr(self.view, 'actionExcel'):
            self.view.actionExcel.triggered.connect(self.handle_export_excel)

        if hasattr(self.view, 'actionAccess'):
            self.view.actionAccess.triggered.connect(self.handle_export_access)

    def handle_export_csv(self):
        """处理CSV导出"""
        data_count = self.view.get_data_count()
        if data_count == 0:
            QMessageBox.information(self.view, "提示", "当前没有数据可以导出。")
            return

        # 选择保存文件路径
        file_path, _ = QFileDialog.getSaveFileName(
            self.view,
            "导出CSV文件",
            f"千分表数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV文件 (*.csv)"
        )

        if not file_path:
            return

        try:
            self.view.update_status("正在导出CSV文件...")

            # 获取表格数据
            table_data = self.get_table_data()

            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)

                # 写入表头
                writer.writerow(['时间', '数值(mm)'])

                # 写入数据
                for row_data in table_data:
                    writer.writerow(row_data)

            self.view.update_status(f"CSV文件导出成功：{os.path.basename(file_path)}")
            QMessageBox.information(self.view, "导出成功", f"数据已成功导出到：\n{file_path}")

        except Exception as e:
            self.view.update_status(f"CSV导出失败：{str(e)}")
            QMessageBox.critical(self.view, "导出失败", f"CSV文件导出失败：\n{str(e)}")

    def handle_export_excel(self):
        """处理Excel导出"""
        if not EXCEL_AVAILABLE:
            QMessageBox.warning(
                self.view,
                "功能不可用",
                "Excel导出功能需要安装pandas和openpyxl库。\n\n"
                "请运行以下命令安装：\n"
                "pip install pandas openpyxl"
            )
            return

        data_count = self.view.get_data_count()
        if data_count == 0:
            QMessageBox.information(self.view, "提示", "当前没有数据可以导出。")
            return

        # 选择保存文件路径
        file_path, _ = QFileDialog.getSaveFileName(
            self.view,
            "导出Excel文件",
            f"千分表数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel文件 (*.xlsx)"
        )

        if not file_path:
            return

        try:
            self.view.update_status("正在导出Excel文件...")

            # 获取表格数据
            table_data = self.get_table_data()

            # 创建DataFrame
            df = pd.DataFrame(table_data, columns=['时间', '数值(mm)'])

            # 写入Excel文件
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='千分表数据', index=False)

                # 获取工作表并设置格式
                worksheet = writer.sheets['千分表数据']

                # 设置列宽
                worksheet.column_dimensions['A'].width = 15  # 时间列
                worksheet.column_dimensions['B'].width = 12  # 数值列
                worksheet.column_dimensions['C'].width = 10  # 备注列

                # 添加统计信息工作表
                stats_data = [
                    ['统计项目', '数值'],
                    ['总记录数', len(table_data)],
                    ['最大值', max([float(row[1]) for row in table_data]) if table_data else 0],
                    ['最小值', min([float(row[1]) for row in table_data]) if table_data else 0],
                    ['平均值', sum([float(row[1]) for row in table_data]) / len(table_data) if table_data else 0],
                    ['导出时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                ]

                stats_df = pd.DataFrame(stats_data[1:], columns=stats_data[0])
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)

            self.view.update_status(f"Excel文件导出成功：{os.path.basename(file_path)}")
            QMessageBox.information(self.view, "导出成功", f"数据已成功导出到：\n{file_path}")

        except Exception as e:
            self.view.update_status(f"Excel导出失败：{str(e)}")
            QMessageBox.critical(self.view, "导出失败", f"Excel文件导出失败：\n{str(e)}")

    def handle_export_access(self):
        """处理Access数据库导出（使用SQLite作为替代）"""
        if not ACCESS_AVAILABLE:
            QMessageBox.warning(
                self.view,
                "功能不可用",
                "数据库导出功能需要sqlite3库支持。"
            )
            return

        data_count = self.view.get_data_count()
        if data_count == 0:
            QMessageBox.information(self.view, "提示", "当前没有数据可以导出。")
            return

        # 选择保存文件路径
        file_path, _ = QFileDialog.getSaveFileName(
            self.view,
            "导出SQLite数据库文件",
            f"千分表数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            "SQLite数据库文件 (*.db);;所有文件 (*.*)"
        )

        if not file_path:
            return

        try:
            self.view.update_status("正在导出数据库文件...")

            # 获取表格数据
            table_data = self.get_table_data()

            # 创建SQLite数据库
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()

            # 创建数据表
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS gauge_data
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               timestamp
                               TEXT
                               NOT
                               NULL,
                               value
                               REAL
                               NOT
                               NULL,
                               created_at
                               DATETIME
                               DEFAULT
                               CURRENT_TIMESTAMP
                           )
                           ''')

            # 插入数据
            for row_data in table_data:
                cursor.execute(
                    'INSERT INTO gauge_data (timestamp, value) VALUES (?, ?)',
                    row_data
                )

            # 创建统计视图
            cursor.execute('''
                           CREATE VIEW IF NOT EXISTS data_statistics AS
                           SELECT COUNT(*)                     as total_records,
                                  MAX(value)                   as max_value,
                                  MIN(value)                   as min_value,
                                  AVG(value)                   as avg_value,
                                  datetime('now', 'localtime') as export_time
                           FROM gauge_data
                           ''')

            # 提交并关闭
            conn.commit()
            conn.close()

            self.view.update_status(f"数据库文件导出成功：{os.path.basename(file_path)}")
            QMessageBox.information(
                self.view,
                "导出成功",
                f"数据已成功导出到SQLite数据库：\n{file_path}\n\n"
                f"注意：由于技术限制，导出为SQLite格式而非Access格式。\n"
                f"SQLite数据库可以用多种工具打开，包括DB Browser for SQLite等。"
            )

        except Exception as e:
            self.view.update_status(f"数据库导出失败：{str(e)}")
            QMessageBox.critical(self.view, "导出失败", f"数据库文件导出失败：\n{str(e)}")

    def change_device_baudrate(self, new_baudrate, detected_baudrate):
        """修改设备波特率"""
        current_port = self.view.port_comboBox.currentText()

        try:
            # 使用检测到的波特率连接设备，而不是当前界面设置的波特率
            temp_reader = GaugeReader(current_port, detected_baudrate)
            temp_reader.connect()

            # 修改设备波特率
            success = temp_reader.change_baudrate(new_baudrate)
            temp_reader.disconnect()

            if success:
                # 更新界面波特率设置
                self.view.baudrate_comboBox.setCurrentText(str(new_baudrate))
                self.view.update_status(f"设备波特率已修改为 {new_baudrate}，请重新连接设备")

                QMessageBox.information(
                    self.view,
                    "波特率修改成功",
                    f"设备波特率已修改为 {new_baudrate} bps\n\n"
                    f"请点击'连接'按钮重新连接设备。"
                )
            else:
                QMessageBox.warning(
                    self.view,
                    "波特率修改失败",
                    "无法修改设备波特率，请检查设备连接。"
                )
                self.view.update_status("设备波特率修改失败")

        except Exception as e:
            QMessageBox.critical(
                self.view,
                "波特率修改错误",
                f"修改设备波特率时发生错误：\n{str(e)}"
            )
            self.view.update_status(f"波特率修改错误: {str(e)}")