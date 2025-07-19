#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千分表485转接盒读取器 - 全新版本
简单、稳定、快速的数据读取程序
"""

import serial
import time
import struct
import threading
from datetime import datetime


class GaugeReader:
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
            print(f"✅ 连接成功: {self.port} @ {self.baudrate}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.serial:
            self.serial.close()
            print("📴 连接已断开")

    def read_value(self):
        """读取一次数值"""
        if not self.serial:
            return None

        # 构建读取命令: 01 04 00 37 00 02 + CRC
        cmd = [0x01, 0x04, 0x00, 0x37, 0x00, 0x02]
        crc = self.crc16(cmd)
        cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

        try:
            # 优化：减少清空缓冲区的频率
            self.serial.write(bytes(cmd))

            # 根据波特率调整等待时间
            if self.baudrate >= 57600:
                time.sleep(0.01)  # 高波特率用更短等待
            elif self.baudrate >= 19200:
                time.sleep(0.02)
            else:
                time.sleep(0.05)  # 9600需要更长等待

            response = self.serial.read(9)  # 只读取需要的9字节
            if len(response) >= 9:
                # 解析数据: 地址 功能码 字节数 数据(4字节) CRC(2字节)
                if response[0] == 0x01 and response[1] == 0x04 and response[2] == 0x04:
                    raw_data = struct.unpack('>i', response[3:7])[0]
                    # 修改这里：改为除以1000而不是10000
                    return raw_data / 1000.0
            return None
        except Exception as e:
            print(f"读取错误: {e}")
            return None

    def zero(self):
        """清零操作"""
        if not self.serial:
            return False

        # 构建清零命令: 01 06 00 36 00 01 + CRC
        cmd = [0x01, 0x06, 0x00, 0x36, 0x00, 0x01]
        crc = self.crc16(cmd)
        cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

        try:
            self.serial.write(bytes(cmd))
            time.sleep(0.2)
            response = self.serial.read(10)
            return len(response) >= 8
        except:
            return False

    def continuous_read(self, interval=0.2):
        """连续读取"""
        # 计算理论最大频率
        bytes_per_transaction = 17  # 8字节发送 + 9字节接收
        theoretical_max_freq = (self.baudrate / 10) / bytes_per_transaction

        print(f"🔄 开始连续读取 (间隔:{interval}秒)")
        print(f"📡 当前波特率: {self.baudrate}")
        print(f"📊 理论最大频率: {theoretical_max_freq:.1f}Hz")
        if interval < (1 / theoretical_max_freq):
            print(f"⚠️  设置间隔过小，实际频率会受波特率限制")
        print("按 Ctrl+C 停止")
        print("-" * 60)

        self.running = True
        count = 0
        start_time = time.time()
        last_time = start_time

        try:
            while self.running:
                loop_start = time.time()

                value = self.read_value()
                if value is not None:
                    count += 1
                    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    elapsed = time.time() - start_time
                    current_freq = count / elapsed if elapsed > 0 else 0

                    # 计算瞬时频率（最近1秒的平均）
                    instant_freq = 1 / (time.time() - last_time) if count > 1 else 0
                    last_time = time.time()

                    print(
                        f"[{now}] #{count:4d} 位移:{value:+8.3f}mm 平均:{current_freq:.1f}Hz 瞬时:{instant_freq:.1f}Hz")
                else:
                    print("❌ 读取失败")

                # 精确控制间隔
                elapsed_loop = time.time() - loop_start
                sleep_time = max(0, interval - elapsed_loop)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n⏹️ 停止读取")
            elapsed = time.time() - start_time
            if elapsed > 0:
                print(f"📊 总计读取 {count} 次，平均频率: {count / elapsed:.2f}Hz")
        finally:
            self.running = False

    def change_baudrate(self, new_rate):
        """修改波特率"""
        if not self.serial:
            return False

        # 波特率对照
        rates = {9600: 0x0096, 19200: 0x0192, 38400: 0x0384,
                 57600: 0x0576, 115200: 0x1152}

        if new_rate not in rates:
            print(f"不支持的波特率: {new_rate}")
            return False

        rate_hex = rates[new_rate]
        cmd = [0x01, 0x06, 0x00, 0x31, (rate_hex >> 8) & 0xFF, rate_hex & 0xFF]
        crc = self.crc16(cmd)
        cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

        try:
            self.serial.write(bytes(cmd))
            time.sleep(0.3)
            response = self.serial.read(10)
            if len(response) >= 8:
                print(f"✅ 波特率已修改为 {new_rate}")
                print("⚠️  请重启程序并修改连接参数")
                return True
            return False
        except:
            return False

    def auto_detect_baudrate(self):
        """自动检测波特率"""
        rates = [9600, 19200, 38400, 57600, 115200]

        for rate in rates:
            print(f"尝试 {rate}...")
            try:
                if self.serial:
                    self.serial.close()

                test_serial = serial.Serial(
                    port=self.port,
                    baudrate=rate,
                    bytesize=8,
                    parity='N',
                    stopbits=1,
                    timeout=0.5
                )

                # 发送测试命令
                cmd = [0x01, 0x04, 0x00, 0x37, 0x00, 0x02]
                crc = self.crc16(cmd)
                cmd.extend([crc & 0xFF, (crc >> 8) & 0xFF])

                test_serial.reset_input_buffer()
                test_serial.write(bytes(cmd))
                time.sleep(0.1)
                response = test_serial.read(20)

                if len(response) >= 9 and response[0] == 0x01 and response[1] == 0x04:
                    print(f"✅ 检测到波特率: {rate}")
                    self.baudrate = rate
                    self.serial = test_serial
                    return True
                else:
                    test_serial.close()

            except:
                continue

        print("❌ 未检测到设备")
        return False


def main():
    """主程序"""
    print("🔧 千分表读取器")
    print("=" * 40)

    gauge = GaugeReader()

    # 尝试连接
    if not gauge.connect():
        print("🔍 尝试自动检测...")
        if not gauge.auto_detect_baudrate():
            print("❌ 无法连接设备")
            return

    try:
        while True:
            print("\n选择操作:")
            print("1. 单次读取")
            print("2. 连续读取")
            print("3. 清零")
            print("4. 修改波特率")
            print("5. 自动检测波特率")
            print("0. 退出")

            choice = input("请选择: ").strip()

            if choice == '1':
                value = gauge.read_value()
                if value is not None:
                    print(f"📏 当前读数: {value:+8.3f}mm")
                else:
                    print("❌ 读取失败")

            elif choice == '2':
                print(f"\n当前波特率: {gauge.baudrate}")
                # 计算最大频率
                max_freq = (gauge.baudrate / 10) / 17
                print(f"理论最大频率: {max_freq:.1f}Hz")
                print("推荐设置:")
                if gauge.baudrate >= 57600:
                    print("  0.05 - 20Hz (高速)")
                    print("  0.02 - 50Hz (极速)")
                elif gauge.baudrate >= 19200:
                    print("  0.1 - 10Hz")
                    print("  0.05 - 20Hz")
                else:
                    print("  0.2 - 5Hz")
                    print("  0.5 - 2Hz (当前波特率限制)")
                    print("  ⚠️  建议先升级波特率到38400+")

                try:
                    interval = float(input("读取间隔(秒,默认0.2): ") or "0.2")
                    gauge.continuous_read(interval)
                except ValueError:
                    print("❌ 无效输入")

            elif choice == '3':
                if gauge.zero():
                    print("✅ 清零成功")
                    # 验证清零结果
                    time.sleep(0.5)
                    value = gauge.read_value()
                    if value is not None:
                        print(f"📏 清零后读数: {value:+8.3f}mm")
                else:
                    print("❌ 清零失败")

            elif choice == '4':
                print("支持的波特率:")
                rates = [9600, 19200, 38400, 57600, 115200]
                for i, rate in enumerate(rates, 1):
                    print(f"  {i}. {rate}")

                try:
                    idx = int(input("选择(1-5): ")) - 1
                    if 0 <= idx < len(rates):
                        if gauge.change_baudrate(rates[idx]):
                            break  # 需要重启程序
                    else:
                        print("❌ 无效选择")
                except ValueError:
                    print("❌ 无效输入")

            elif choice == '5':
                gauge.auto_detect_baudrate()

            elif choice == '0':
                break

            else:
                print("❌ 无效选择")

    except KeyboardInterrupt:
        print("\n程序被中断")
    finally:
        gauge.disconnect()


if __name__ == "__main__":
    main()