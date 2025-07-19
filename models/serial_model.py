import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from models.gauge_reader import GaugeReader


class SerialModel(QObject):
    """串口通信模型 - 集成GaugeReader"""

    # 信号定义
    dataReceived = pyqtSignal(float)
    connectionStatusChanged = pyqtSignal(bool)
    errorOccurred = pyqtSignal(str)
    autoDetectCompleted = pyqtSignal(int)  # 检测到的波特率，None表示失败

    def __init__(self):
        super().__init__()
        self.gauge_reader = None
        self._is_reading = False

    def get_available_ports(self):
        """获取可用串口列表"""
        return GaugeReader.get_available_ports()

    def auto_detect_baudrate(self, port):
        """自动检测波特率"""
        try:
            detected_rate = GaugeReader.auto_detect_baudrate(port)
            self.autoDetectCompleted.emit(detected_rate if detected_rate else 0)
            return detected_rate
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self.autoDetectCompleted.emit(0)
            return None

    def connect(self, port, baudrate):
        """连接串口"""
        try:
            self.gauge_reader = GaugeReader(port, baudrate)
            self.gauge_reader.connect()

            # 测试通信
            if self.gauge_reader.test_communication():
                self.connectionStatusChanged.emit(True)
                return True
            else:
                self.gauge_reader.disconnect()
                raise Exception("设备通信测试失败，请检查设备连接")

        except Exception as e:
            self.errorOccurred.emit(str(e))
            self.connectionStatusChanged.emit(False)
            return False

    def disconnect(self):
        """断开串口"""
        if self.gauge_reader:
            self.gauge_reader.disconnect()
            self.gauge_reader = None
        self.connectionStatusChanged.emit(False)

    def read_value(self):
        """读取数值"""
        if self.gauge_reader:
            try:
                value = self.gauge_reader.read_value()
                print(f"Debug: GaugeReader返回值: {value}")  # 添加这行
                self.dataReceived.emit(value)
                return value
            except Exception as e:
                print(f"Debug: GaugeReader异常: {e}")  # 添加这行
                self.errorOccurred.emit(str(e))
                return None
        return None

    def zero_device(self):
        """设备清零"""
        if self.gauge_reader:
            try:
                return self.gauge_reader.zero()
            except Exception as e:
                self.errorOccurred.emit(str(e))
                return False
        return False