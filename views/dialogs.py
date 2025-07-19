import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

# ==================== 自动检测对话框 ====================
class AutoDetectDialog(QDialog):
    """自动检测结果对话框"""

    def __init__(self, current_baudrate, detected_baudrate, parent=None):
        super().__init__(parent)
        self.current_baudrate = current_baudrate
        self.detected_baudrate = detected_baudrate
        self.selected_baudrate = None

        self.setup_ui()

    def setup_ui(self):
        """设置对话框UI"""
        self.setWindowTitle("自动检测结果")
        self.setFixedSize(350, 200)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self)

        # 结果显示
        if self.detected_baudrate:
            icon_label = QLabel("✅")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("font-size: 24px;")
            layout.addWidget(icon_label)

            result_label = QLabel("检测成功！")
            result_label.setAlignment(Qt.AlignCenter)
            result_label.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
            layout.addWidget(result_label)

            # 波特率对比
            info_layout = QFormLayout()
            current_label = QLabel(f"{self.current_baudrate}")
            current_label.setStyleSheet("font-weight: bold;")
            detected_label = QLabel(f"{self.detected_baudrate}")
            detected_label.setStyleSheet("font-weight: bold; color: blue;")

            info_layout.addRow("当前设置:", current_label)
            info_layout.addRow("检测结果:", detected_label)
            layout.addLayout(info_layout)

            # 按钮
            button_layout = QHBoxLayout()

            use_detected_btn = QPushButton("使用自动设置")
            use_detected_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
            use_detected_btn.clicked.connect(self.use_detected)

            use_current_btn = QPushButton("使用当前设置")
            use_current_btn.clicked.connect(self.use_current)

            button_layout.addWidget(use_detected_btn)
            button_layout.addWidget(use_current_btn)
            layout.addLayout(button_layout)

        else:
            # 检测失败
            icon_label = QLabel("❌")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("font-size: 24px;")
            layout.addWidget(icon_label)

            result_label = QLabel("未检测到设备")
            result_label.setAlignment(Qt.AlignCenter)
            result_label.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")
            layout.addWidget(result_label)

            suggestion_label = QLabel("请检查：\n• 设备是否正确连接\n• 串口是否被其他程序占用\n• 设备是否通电")
            suggestion_label.setStyleSheet("color: #666; margin: 10px;")
            layout.addWidget(suggestion_label)

            # 按钮
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(self.reject)
            layout.addWidget(ok_btn)

    def use_detected(self):
        """使用检测到的波特率"""
        self.selected_baudrate = self.detected_baudrate
        self.accept()

    def use_current(self):
        """使用当前波特率"""
        self.selected_baudrate = self.current_baudrate
        self.accept()


# ==================== 连接错误对话框 ====================
class ConnectionErrorDialog(QDialog):
    """连接错误对话框"""

    def __init__(self, error_message, port, baudrate, parent=None):
        super().__init__(parent)
        self.error_message = error_message
        self.port = port
        self.baudrate = baudrate

        self.setup_ui()

    def setup_ui(self):
        """设置对话框UI"""
        self.setWindowTitle("连接失败")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # 错误图标
        icon_label = QLabel("❌")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)

        # 错误标题
        title_label = QLabel("设备连接失败")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red; margin: 10px;")
        layout.addWidget(title_label)

        # 连接信息
        info_group = QGroupBox("连接信息")
        info_layout = QFormLayout(info_group)
        info_layout.addRow("串口:", QLabel(self.port))
        info_layout.addRow("波特率:", QLabel(str(self.baudrate)))
        info_layout.addRow("错误信息:", QLabel(self.error_message))
        layout.addWidget(info_group)

        # 建议信息
        suggestion_group = QGroupBox("解决建议")
        suggestion_layout = QVBoxLayout(suggestion_group)

        suggestions = self.get_suggestions()
        for suggestion in suggestions:
            suggestion_label = QLabel(f"• {suggestion}")
            suggestion_label.setWordWrap(True)
            suggestion_label.setStyleSheet("margin: 2px;")
            suggestion_layout.addWidget(suggestion_label)

        layout.addWidget(suggestion_group)

        # 按钮
        button_layout = QHBoxLayout()

        auto_detect_btn = QPushButton("自动检测")
        auto_detect_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        auto_detect_btn.clicked.connect(self.auto_detect)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)

        button_layout.addWidget(auto_detect_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)

    def get_suggestions(self):
        """根据错误类型获取建议"""
        error_lower = self.error_message.lower()

        suggestions = []

        if "access is denied" in error_lower or "拒绝访问" in error_lower:
            suggestions.extend([
                "串口被其他程序占用，请关闭相关程序",
                "尝试重新插拔USB设备",
                "以管理员权限运行程序"
            ])
        elif "could not open port" in error_lower or "无法打开" in error_lower:
            suggestions.extend([
                "检查设备是否正确连接到电脑",
                "确认选择的串口号是否正确",
                "尝试重新插拔USB设备"
            ])
        elif "timeout" in error_lower or "超时" in error_lower:
            suggestions.extend([
                "检查设备是否通电",
                "确认波特率设置是否正确",
                "检查串口线是否连接良好"
            ])
        else:
            suggestions.extend([
                "检查设备是否正确连接并通电",
                "确认串口和波特率设置",
                "尝试使用自动检测功能",
                "检查设备驱动是否安装正确"
            ])

        return suggestions

    def auto_detect(self):
        """触发自动检测"""
        self.done(2)  # 返回特殊值表示需要自动检测


class IntervalWarningDialog(QDialog):
    """读取间隔警告对话框"""

    def __init__(self, current_interval, current_baudrate, min_interval, suggested_baudrate, parent=None):
        super().__init__(parent)
        self.current_interval = current_interval
        self.current_baudrate = current_baudrate
        self.min_interval = min_interval
        self.suggested_baudrate = suggested_baudrate
        self.user_choice = None

        self.setup_ui()

    def setup_ui(self):
        """设置对话框UI"""
        self.setWindowTitle("读取间隔警告")
        self.setFixedSize(500, 700)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self)

        # 警告图标
        icon_label = QLabel("⚠️")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)

        # 警告标题
        title_label = QLabel("读取间隔过小")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF9800; margin: 10px;")
        layout.addWidget(title_label)

        # 提示信息
        info_text = f"设置的读取间隔 ({self.current_interval:.3f}s) 过小，当前波特率无法支持此频率的数据传输。"
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: #666; margin: 10px; padding: 10px; background-color: #FFF3E0; border-radius: 5px;")
        layout.addWidget(info_label)

        # 详细信息
        detail_group = QGroupBox("详细信息")
        detail_layout = QFormLayout(detail_group)

        # 当前设置
        current_baudrate_label = QLabel(f"{self.current_baudrate} bps")
        current_baudrate_label.setStyleSheet("font-weight: bold;")
        detail_layout.addRow("当前波特率:", current_baudrate_label)

        current_interval_label = QLabel(f"{self.current_interval:.3f} 秒")
        current_interval_label.setStyleSheet("font-weight: bold; color: red;")
        detail_layout.addRow("设置间隔:", current_interval_label)

        min_interval_label = QLabel(f"{self.min_interval:.3f} 秒")
        min_interval_label.setStyleSheet("font-weight: bold; color: orange;")
        detail_layout.addRow("最小间隔:", min_interval_label)

        # 建议设置
        suggested_baudrate_label = QLabel(f"{self.suggested_baudrate} bps")
        suggested_baudrate_label.setStyleSheet("font-weight: bold; color: green;")
        detail_layout.addRow("建议波特率:", suggested_baudrate_label)

        layout.addWidget(detail_group)

        # 说明文本
        explanation = QLabel(
            "💡 提示：更高的波特率可以支持更快的数据读取频率。\n"
            "数据传输需要时间来发送命令和接收响应。"
        )
        explanation.setStyleSheet(
            "color: #555; font-size: 11px; margin: 10px; padding: 8px; background-color: #F5F5F5; border-radius: 3px;")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        # 按钮
        button_layout = QHBoxLayout()

        # 使用建议波特率按钮
        use_suggested_btn = QPushButton(f"使用建议波特率 ({self.suggested_baudrate})")
        use_suggested_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        use_suggested_btn.clicked.connect(self.use_suggested_baudrate)

        # 调整间隔按钮
        adjust_interval_btn = QPushButton(f"调整为最小间隔 ({self.min_interval:.3f}s)")
        adjust_interval_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        adjust_interval_btn.clicked.connect(self.adjust_interval)

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                border: 1px solid #ddd;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(use_suggested_btn)
        button_layout.addWidget(adjust_interval_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def use_suggested_baudrate(self):
        """使用建议的波特率"""
        self.user_choice = "baudrate"
        self.accept()

    def adjust_interval(self):
        """调整为最小间隔"""
        self.user_choice = "interval"
        self.accept()


class SingleReadDialog(QDialog):
    """单次读取结果对话框"""

    def __init__(self, value, port, baudrate, parent=None):
        super().__init__(parent)
        self.value = value
        self.port = port
        self.baudrate = baudrate

        self.setup_ui()

    def setup_ui(self):
        """设置对话框UI"""
        self.setWindowTitle("单次读取结果")

        # 使用更可靠的方法设置尺寸
        self.resize(500, 600)
        self.setMinimumSize(500, 600)
        self.setMaximumSize(500, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # 成功图标 - 简化样式
        icon_label = QLabel("📏")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)

        # 标题 - 简化样式
        title_label = QLabel("读取成功")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
        layout.addWidget(title_label)

        # 数值显示 - 大幅简化
        value_group = QGroupBox("测量结果")
        value_layout = QVBoxLayout(value_group)
        value_layout.setSpacing(10)

        # 主数值显示 - 移除复杂样式
        value_label = QLabel(f"{self.value:+8.3f}")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: blue; padding: 10px;")
        value_layout.addWidget(value_label)

        # 单位标签
        unit_label = QLabel("毫米 (mm)")
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet("font-size: 14px; color: gray;")
        value_layout.addWidget(unit_label)

        layout.addWidget(value_group)

        # 连接信息 - 简化
        info_group = QGroupBox("连接信息")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)

        # 使用简单的标签，不用FormLayout
        port_info = QLabel(f"串口: {self.port}")
        port_info.setStyleSheet("font-size: 14px; padding: 5px;")
        info_layout.addWidget(port_info)

        baudrate_info = QLabel(f"波特率: {self.baudrate} bps")
        baudrate_info.setStyleSheet("font-size: 14px; padding: 5px;")
        info_layout.addWidget(baudrate_info)

        # 时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_info = QLabel(f"读取时间: {timestamp}")
        time_info.setStyleSheet("font-size: 14px; color: gray; padding: 5px;")
        info_layout.addWidget(time_info)

        layout.addWidget(info_group)

        # 添加一些空间
        layout.addSpacing(20)

        # 确定按钮 - 简化样式
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("font-size: 14px; padding: 10px 30px;")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)


# ==================== 清零确认对话框 ====================
class ZeroConfirmDialog(QDialog):
    """清零确认对话框"""

    def __init__(self, data_count, parent=None):
        super().__init__(parent)
        self.data_count = data_count

        self.setup_ui()

    def setup_ui(self):
        """设置对话框UI"""
        self.setWindowTitle("确认清零操作")
        self.setFixedSize(400, 280)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self)

        # 警告图标
        icon_label = QLabel("⚠️")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)

        # 警告标题
        title_label = QLabel("确认清零操作")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF9800; margin: 10px;")
        layout.addWidget(title_label)

        # 警告信息
        warning_text = "此操作将执行以下动作："
        warning_label = QLabel(warning_text)
        warning_label.setAlignment(Qt.AlignCenter)
        warning_label.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(warning_label)

        # 操作列表
        action_group = QGroupBox("将要执行的操作")
        action_layout = QVBoxLayout(action_group)

        # 设备清零
        device_action = QLabel("🔧 将千分表设备清零归位")
        device_action.setStyleSheet("color: #FF6B35; font-weight: bold; padding: 5px;")
        action_layout.addWidget(device_action)

        # 清空数据
        if self.data_count > 0:
            data_action = QLabel(f"🗑️ 清空表格中的 {self.data_count} 条数据记录")
            data_action.setStyleSheet("color: #FF6B35; font-weight: bold; padding: 5px;")
            action_layout.addWidget(data_action)
        else:
            data_action = QLabel("📝 当前表格中无数据")
            data_action.setStyleSheet("color: #666; padding: 5px;")
            action_layout.addWidget(data_action)

        layout.addWidget(action_group)

        # 提醒信息
        note_label = QLabel("💡 注意：此操作不可撤销，请确认后继续。")
        note_label.setStyleSheet("""
            color: #555; 
            background-color: #FFF3E0; 
            padding: 10px; 
            border-radius: 4px;
            border-left: 4px solid #FF9800;
            margin: 10px 0;
        """)
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        # 按钮
        button_layout = QHBoxLayout()

        # 确认按钮
        confirm_btn = QPushButton("确认清零")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #e55a2e;
            }
        """)
        confirm_btn.clicked.connect(self.accept)

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                border-radius: 4px;
                border: 1px solid #ddd;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置对话框UI"""
        self.setWindowTitle("关于 PGaugeReader")
        self.setFixedSize(500, 1000)
        self.setMaximumSize(500, 1000)
        self.setMinimumSize(500, 1000)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 软件图标区域
        icon_layout = QHBoxLayout()
        icon_label = QLabel("📏")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_layout.addWidget(icon_label)
        layout.addLayout(icon_layout)

        # 软件名称
        name_label = QLabel("PGaugeReader")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: #2E86AB; 
            margin: 10px 0;
        """)
        layout.addWidget(name_label)

        # 版本信息
        version_label = QLabel("版本 1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("font-size: 16px; color: #666; margin-bottom: 20px;")
        layout.addWidget(version_label)

        # 软件描述
        desc_label = QLabel("专业的千分表数据读取软件")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 14px; color: #555; margin-bottom: 20px;")
        layout.addWidget(desc_label)

        # 详细信息区域
        info_group = QGroupBox("软件信息")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(10)

        # 基础信息
        author_label = QLabel("Peler Yuan")
        author_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
        info_layout.addRow("👨‍💻 作者:", author_label)

        sponsor_label = QLabel("Lukas Zhao")
        sponsor_label.setStyleSheet("font-weight: bold; color: #FF6B35;")
        info_layout.addRow("💰 赞助:", sponsor_label)

        license_label = QLabel("GPLv3")
        license_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        info_layout.addRow("📄 许可证:", license_label)

        # 技术信息
        tech_label = QLabel("PyQt5 + Python")
        tech_label.setStyleSheet("font-weight: bold; color: #9C27B0;")
        info_layout.addRow("🛠️ 技术栈:", tech_label)

        protocol_label = QLabel("Modbus RTU over RS485")
        protocol_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        info_layout.addRow("📡 通信协议:", protocol_label)

        support_label = QLabel("千分表、数显卡尺等")
        support_label.setStyleSheet("font-weight: bold; color: #607D8B;")
        info_layout.addRow("🔧 支持设备:", support_label)

        layout.addWidget(info_group)

        # 功能特点
        features_group = QGroupBox("功能特点")
        features_layout = QVBoxLayout(features_group)

        features = [
            "🚀 自动检测设备和波特率",
            "📊 实时数据读取和图表显示",
            "💾 多格式数据导出 (CSV, Excel, Access)",
            "⚡ 高速连续读取，支持115200波特率",
            "🎯 智能读取间隔验证和优化建议",
            "🔄 设备清零和数据管理",
            "🎨 现代化用户界面设计"
        ]

        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setStyleSheet("padding: 3px; color: #333;")
            features_layout.addWidget(feature_label)

        layout.addWidget(features_group)

        # 版权信息
        copyright_label = QLabel("© 2025 Peler Yuan. All rights reserved.")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            color: #888; 
            font-size: 12px; 
            padding: 10px; 
            border-top: 1px solid #ddd;
            margin-top: 10px;
        """)
        layout.addWidget(copyright_label)

        # 感谢信息
        thanks_label = QLabel("感谢您使用 PGaugeReader！")
        thanks_label.setAlignment(Qt.AlignCenter)
        thanks_label.setStyleSheet("""
            color: #2E86AB; 
            font-size: 14px; 
            font-weight: bold;
            padding: 5px;
            background-color: #F0F8FF;
            border-radius: 5px;
            margin: 10px 0;
        """)
        layout.addWidget(thanks_label)

        # 确定按钮
        button_layout = QHBoxLayout()

        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E86AB;
                color: white;
                font-weight: bold;
                padding: 10px 30px;
                border-radius: 5px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        ok_btn.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)