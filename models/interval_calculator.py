class IntervalCalculator:
    """读取间隔计算工具"""

    @staticmethod
    def calculate_min_interval(baudrate):
        """计算指定波特率下的最小读取间隔

        Args:
            baudrate: 波特率

        Returns:
            float: 最小间隔（秒）
        """
        # Modbus RTU通信分析：
        # 发送命令: 8字节 (01 04 00 37 00 02 CRC_L CRC_H)
        # 接收响应: 9字节 (01 04 04 DATA1 DATA2 DATA3 DATA4 CRC_L CRC_H)
        # 总计: 17字节

        # 每字节包含: 1起始位 + 8数据位 + 1停止位 = 10位
        total_bits = 17 * 10

        # 传输时间 = 总位数 / 波特率
        transmission_time = total_bits / baudrate

        # 加上处理延迟和安全裕量 (50%)
        min_interval = transmission_time * 1.5

        return min_interval

    @staticmethod
    def suggest_baudrate(target_interval):
        """根据目标间隔建议波特率

        Args:
            target_interval: 目标读取间隔（秒）

        Returns:
            int: 建议的波特率
        """
        supported_baudrates = [9600, 19200, 38400, 57600, 115200]

        for baudrate in supported_baudrates:
            min_interval = IntervalCalculator.calculate_min_interval(baudrate)
            if min_interval <= target_interval:
                return baudrate

        # 如果最高波特率都不够，返回最高波特率
        return supported_baudrates[-1]

    @staticmethod
    def is_interval_valid(interval, baudrate):
        """检查间隔是否有效

        Args:
            interval: 读取间隔（秒）
            baudrate: 波特率

        Returns:
            bool: 是否有效
        """
        min_interval = IntervalCalculator.calculate_min_interval(baudrate)
        return interval >= min_interval