import sys
import time
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class ContinuousReadWorker(QObject):
    """连续读取工作线程"""

    dataRead = pyqtSignal(float, str)  # 数据值, 时间戳
    errorOccurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, serial_model, interval):
        super().__init__()
        self.serial_model = serial_model
        self.interval = interval
        self.running = False

    def start_reading(self):
        """开始读取"""
        self.running = True
        self.run()

    def stop_reading(self):
        """停止读取"""
        self.running = False

    def run(self):
        """执行连续读取"""
        while self.running:
            try:
                if self.serial_model.gauge_reader:
                    value = self.serial_model.gauge_reader.read_value()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    self.dataRead.emit(value, timestamp)
                else:
                    self.errorOccurred.emit("设备连接已断开")
                    break

                # 等待指定间隔
                start_time = time.time()
                while self.running and (time.time() - start_time) < self.interval:
                    time.sleep(0.001)  # 短暂休眠，允许停止信号

            except Exception as e:
                self.errorOccurred.emit(f"读取错误: {str(e)}")
                break

        self.finished.emit()