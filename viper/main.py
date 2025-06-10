import os
import sys
import time
import json
import multiprocessing
from pathlib import Path
from datetime import datetime

import serial
import serial.tools.list_ports
from loguru import logger
from dotenv import find_dotenv, load_dotenv
from PySide6.QtCore import QSharedMemory, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget,
    QMessageBox,
    QVBoxLayout,
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpacerItem,
    QSizePolicy
)


load_dotenv(find_dotenv())

DEV_MODE = os.getenv('DEBUG') == '1'  # None

if DEV_MODE:
    BASE_DIR = Path(__file__).resolve().parent.parent
else:
    BASE_DIR = Path(sys.executable).parent  # 获取可执行文件所在目录

CONFIG_FILE = BASE_DIR / 'params.json'

LOG_DIR = Path(BASE_DIR) / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR.joinpath('{}-scan-sn.log'.format(datetime.now().strftime('%Y%m%d')))

logger.remove()

logger.add(
    LOG_FILE,
    rotation='500MB',
    format='{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}',
    encoding='utf-8',
    enqueue=True,  # 启用异步日志处理
    level='INFO',
    diagnose=False,  # 关闭变量值
    backtrace=False,  # 关闭完整堆栈跟踪
    colorize=False
)

if DEV_MODE:
    logger.add(
        sink=sys.stdout,  # 输出到标准输出流
        format='{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}',  # 日志格式
        level='DEBUG',
        diagnose=False,
        backtrace=False,
        colorize=False,
        enqueue=True
    )


def wait_ms(ms=20):
    time.sleep(ms / 1000.0)
    return


def get_com_ports():
    ports = serial.tools.list_ports.comports()
    com_ports = []
    for port in ports:
        logger.info(port.description)
        if 'Serial Device' in port.description or '串行设备' in port.description:
            com_ports.append(port.device)
    logger.info(f'com_ports: {com_ports}')
    return com_ports


def get_sn(com_port):
    ser = serial.Serial(port=com_port, baudrate=9600, timeout=0)
    sn = ''
    try:
        ser.write(b'\x06\xC7\x04\x00\xF4\x01\xFE\x3A')
        wait_ms(100)
        response = ser.read(64)
        product_info = response.decode('utf-8', 'ignore').strip()
        for line in product_info.splitlines():
            if line.startswith('Product ID:'):
                sn = line.split(':', 1)[1].strip()
                break
        logger.info(f'SN:{sn}')
    finally:
        ser.close()
    return sn


def get_config():
    params_file = CONFIG_FILE
    logger.info(f'params file in: {params_file}')
    config = {}
    if not params_file.exists():
        logger.info('no params file')
        return config
    logger.info('has params file')
    with open(params_file, 'r') as file:
        config = json.load(file)
    return config


def save_config(data_dict):
    params_file = CONFIG_FILE
    with open(params_file, 'w') as file:
        file.write(json.dumps(data_dict, indent=4))
    return


BUTTON_STYLE = '''
    QWidget {
        background: #f8fbfd;
        font-size: 15px;
        color: #222;
    }
    QLineEdit {
        border: 1.5px solid #d0e2f2;
        border-radius: 8px;
        padding: 6px 10px;
        background: #fff;
        font-family: Arial, sans-serif;
        font-size: 14px;
    }
    QLineEdit:focus {
        border: 2px solid #4e97f7;
    }
    QPushButton {
        background: #4e97f7;
        color: #fff;
        border: none;
        border-radius: 7px;
        padding: 7px 22px;
        font-weight: bold;
    }
    QPushButton:disabled {
        background: #b2c8e6;
        color: #eee;
    }
    QLabel {
        color: #3b5770;
    }
'''

SN_KEYS = [
    ('many_sn_a', '烧录A扫描器的SN号：'),
    ('many_sn_b', '烧录B扫描器的SN号：'),
    ('many_sn_c', '烧录C扫描器的SN号：'),
    ('many_sn_x', '复核X扫描器的SN号：'),
    ('many_sn_y', '复核Y扫描器的SN号：'),
    ('many_sn_z', '复核Z扫描器的SN号：'),
]


# 单实例应用
class SingleInstance:

    def __init__(self, key='scan-sn'):
        self.shared_memory = QSharedMemory(key)

    def is_running(self):
        if self.shared_memory.attach():
            return True  # 已有实例在运行
        if self.shared_memory.create(1):  # 创建共享内存
            return False  # 没有其他实例
        return True  # 创建失败，说明已有实例


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Scan SN')
        self.setFixedSize(600, 400)  # 固定窗口大小

        self.config = get_config()
        self.sn_edits = {}

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(24, 18, 24, 18)

        # 顶部区域
        top_hbox = QHBoxLayout()
        self.scan_result_edit = QLineEdit()
        self.scan_result_edit.setPlaceholderText('新扫描到的SN号')
        self.scan_result_edit.setMinimumWidth(210)
        self.scan_result_edit.setMaximumWidth(260)
        self.scan_result_edit.setClearButtonEnabled(True)
        self.scan_result_edit.setReadOnly(True)
        self.scan_result_edit.setFixedHeight(34)
        top_hbox.addWidget(self.scan_result_edit, 4)

        self.btn_find = QPushButton('查找')
        self.btn_find.setCursor(QCursor(Qt.PointingHandCursor))  # noqa
        self.btn_find.setFixedWidth(80)
        self.btn_find.setFixedHeight(34)
        self.btn_find.clicked.connect(self.find_sn)
        top_hbox.addWidget(self.btn_find, 1)

        self.btn_add = QPushButton('添加')
        self.btn_add.setCursor(QCursor(Qt.PointingHandCursor))  # noqa
        self.btn_add.setEnabled(False)
        self.btn_add.setFixedWidth(80)
        self.btn_add.setFixedHeight(34)
        self.btn_add.clicked.connect(self.add_sn)
        top_hbox.addWidget(self.btn_add, 1)

        main_layout.addLayout(top_hbox)

        # SN配置项区域
        for key, label_txt in SN_KEYS:
            row = QHBoxLayout()
            row.setSpacing(7)
            label = QLabel(label_txt)
            edit = QLineEdit()
            edit.setPlaceholderText('请输入SN号')
            edit.setText(self.config.get(key, ''))
            edit.setClearButtonEnabled(True)
            edit.setMinimumWidth(160)
            edit.setMaximumWidth(260)
            edit.setFixedHeight(34)
            self.sn_edits[key] = edit
            row.addWidget(label, 3)
            row.addWidget(edit, 7)
            main_layout.addLayout(row)

        # 占位使下方按钮靠下
        main_layout.addSpacing(10)  # noqa

        # 底部保存按钮
        btn_save = QPushButton('保存')
        btn_save.setCursor(QCursor(Qt.PointingHandCursor))  # noqa
        btn_save.setFixedHeight(34)
        btn_save.setFixedWidth(120)
        btn_save.clicked.connect(self.save)
        font = btn_save.font()
        font.setPointSize(14)
        btn_save.setFont(font)
        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(btn_save)
        bottom_hbox.addStretch()
        main_layout.addLayout(bottom_hbox)

    def find_sn(self):
        # 获取新SN
        all_sn = [edit.text().strip() for edit in self.sn_edits.values() if edit.text().strip()]
        com_ports = get_com_ports()
        new_sn = ''
        for com_port in com_ports:
            sn = get_sn(com_port)
            if sn and sn not in all_sn:
                new_sn = sn
                break
        if new_sn:
            self.scan_result_edit.setText(new_sn)
            self.btn_add.setEnabled(True)
        else:
            self.scan_result_edit.setText('')
            self.btn_add.setEnabled(False)
            QMessageBox.information(self, '未检测到新SN', '未检测到新的SN设备，或SN已存在')

    def add_sn(self):
        sn = self.scan_result_edit.text().strip()
        if not sn:
            return
        for key in SN_KEYS:
            edit = self.sn_edits[key[0]]
            if not edit.text().strip():
                edit.setText(sn)
                self.scan_result_edit.clear()
                self.btn_add.setEnabled(False)
                return
        # 没有空位
        QMessageBox.information(self, 'SN已满', '所有SN都已填写完毕，无法添加')
        self.btn_add.setEnabled(False)

    def save(self):
        data = get_config()
        for key in SN_KEYS:
            data[key[0]] = self.sn_edits[key[0]].text().strip()
        save_config(data)
        QMessageBox.information(self, '保存成功', '配置已保存到文件')


# 捕获所有 主线程 界面按钮及事件的异常
def main_excepthook(exctype, value, tb):
    logger.opt(exception=(exctype, value, tb)).error('主线程界面及事件异常')


multiprocessing.freeze_support()

# 单实例检测
single = SingleInstance()
if single.is_running():
    print('另一个应用程序实例已启动，忽略当前操作')
    sys.exit(0)

sys.excepthook = main_excepthook

app = QApplication(sys.argv)
wd = MainWindow()
wd.setStyleSheet(BUTTON_STYLE)
wd.show()
sys.exit(app.exec())
