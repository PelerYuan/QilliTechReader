import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from models.gauge_reader import GaugeReader

class AutoDetectWorker(QObject):
    """自动检测波特率工作线程"""

    finished = pyqtSignal(int)  # 检测完成信号，参数为检测到的波特率（0表示失败）

    def __init__(self, port):
        super().__init__()
        self.port = port

    def run(self):
        """执行自动检测"""
        try:
            detected_baudrate = GaugeReader.auto_detect_baudrate(self.port)
            if detected_baudrate:
                self.finished.emit(detected_baudrate)
            else:
                self.finished.emit(0)  # 0表示检测失败
        except Exception as e:
            print(f"自动检测异常: {e}")
            self.finished.emit(0)