import sys
import serial
import time
import struct
import threading
from datetime import datetime

class GaugeReader:
    """千分表485转接盒读取器 - 来自你的原始代码"""

    def __init__(self, port='COM7', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.slave_id = 1

    def crc16(self, data):
        """计算Modbus CRC16校验码"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def connect(self):
        """连接串口"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            return True
        except Exception as e:
            raise Exception(f"串口连接失败: {str(e)}")

    def disconnect(self):
        """断开连接"""
        if self.serial and self.serial.is_open:
            self.serial.close()

    def test_communication(self):
        """测试通信是否正常"""
        try:
            if not self.serial or not self.serial.is_open:
                return False

            # 构建读取命令: 01 04 00 37 00 02 + CRC
            cmd = [0x01, 0x04, 0x00, 0x37, 0x00, 0x02]
            crc = self.crc16(cmd)
            cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

            # 清空缓冲区
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            # 发送命令
            self.serial.write(bytes(cmd))
            time.sleep(0.1)

            # 读取响应
            response = self.serial.read(9)

            # 验证响应
            if len(response) >= 9 and response[0] == 0x01 and response[1] == 0x04:
                return True
            return False

        except Exception:
            return False

    def read_value(self):
        """读取一次数值"""
        if not self.serial or not self.serial.is_open:
            raise Exception("串口未连接")

        try:
            # 构建读取命令: 01 04 00 37 00 02 + CRC
            cmd = [0x01, 0x04, 0x00, 0x37, 0x00, 0x02]
            crc = self.crc16(cmd)
            cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

            self.serial.reset_input_buffer()
            self.serial.write(bytes(cmd))
            time.sleep(0.05)

            response = self.serial.read(9)
            if len(response) >= 9:
                if response[0] == 0x01 and response[1] == 0x04 and response[2] == 0x04:
                    raw_data = struct.unpack('>i', response[3:7])[0]
                    # 修改这里：改为除以1000而不是10000
                    return raw_data / 1000.0

            raise Exception("读取数据格式错误")

        except Exception as e:
            raise Exception(f"读取失败: {str(e)}")

    def zero(self):
        """清零操作"""
        if not self.serial or not self.serial.is_open:
            raise Exception("串口未连接")

        try:
            # 构建清零命令: 01 06 00 36 00 01 + CRC
            cmd = [0x01, 0x06, 0x00, 0x36, 0x00, 0x01]
            crc = self.crc16(cmd)
            cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

            self.serial.write(bytes(cmd))
            time.sleep(0.2)
            response = self.serial.read(10)
            return len(response) >= 8
        except Exception as e:
            raise Exception(f"清零失败: {str(e)}")

    def change_baudrate(self, new_rate):
        """修改波特率"""
        if not self.serial or not self.serial.is_open:
            raise Exception("串口未连接")

        # 波特率对照表
        rates = {
            2400: 0x0024,
            4800: 0x0048,
            9600: 0x0096,
            19200: 0x0192,
            38400: 0x0384,
            57600: 0x0576,
            115200: 0x1152
        }

        if new_rate not in rates:
            raise Exception(f"不支持的波特率: {new_rate}")

        try:
            rate_hex = rates[new_rate]
            # 构建修改波特率命令: 01 06 00 31 + 波特率值 + CRC
            cmd = [0x01, 0x06, 0x00, 0x31, (rate_hex >> 8) & 0xFF, rate_hex & 0xFF]
            crc = self.crc16(cmd)
            cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

            self.serial.write(bytes(cmd))
            time.sleep(0.3)  # 等待设备处理
            response = self.serial.read(10)

            if len(response) >= 8:
                return True
            else:
                raise Exception("设备无响应")

        except Exception as e:
            raise Exception(f"修改波特率失败: {str(e)}")

    @staticmethod
    def get_available_ports():
        """获取可用串口列表"""
        import serial.tools.list_ports
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return sorted(ports) if ports else ["未找到串口"]

    @staticmethod
    def auto_detect_baudrate(port):
        """自动检测波特率"""
        rates = [9600, 19200, 38400, 57600, 115200]

        for rate in rates:
            try:
                reader = GaugeReader(port, rate)
                reader.connect()

                if reader.test_communication():
                    reader.disconnect()
                    return rate

                reader.disconnect()

            except Exception:
                continue

        return None