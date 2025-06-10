import ctypes
import time
import logging

from snap7.server import Server
from snap7.type import SrvArea

# 配置日志
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建全局 DB 存储区
db_size = 10240
db_memory = ctypes.create_string_buffer(db_size)


def init_v(server):
    server.register_area(SrvArea.DB, 1, db_memory)  # 绑定DB1到全局存储


def setup_server():
    server = Server()
    server.create()
    init_v(server)  # 初始化DB存储
    server.start_to(ip='0.0.0.0')
    return server


# 持续处理 服务器 事件
def handle_events(server):
    try:
        while True:
            event = server.pick_event()  # 不会自动清除事件队列或去重
            if event:
                logger.info(f'收到事件: {server.event_text(event)}')
                server.clear_events()  # 清除已处理的事件，防止重复输出
            status, cpu_status, client_count = server.get_status()  # 检查服务器状态
            if client_count > 0:
                logger.info(f'已连接的客户端数量: {client_count}')
            time.sleep(1)  # 减少CPU使用率
    except KeyboardInterrupt:
        logger.info('接收到中断信号，正在停止服务器...')
    except Exception as e:
        logger.error(f'发生错误: {e}')
    finally:
        server.destroy()
        logger.info('服务器已停止')


def main():
    server = setup_server()
    handle_events(server)


if __name__ == '__main__':
    main()
