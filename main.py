import sys

from PyQt5.QtWidgets import QApplication

from controllers.main_controller import MainController


def main():
    """主程序"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("千分表数据读取器")
    app.setApplicationVersion("1.0.0")

    # 创建主控制器
    controller = MainController()
    controller.show()

    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()