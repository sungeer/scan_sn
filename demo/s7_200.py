from snap7 import client, util  # python -m pip install python-snap7
from snap7.type import Area

BYTE_INDEX = 1010  # VW1010 的起始字节
BIT_INDEX = 2  # 位索引 V1010.2
DB_NUMBER = 1


def get_plc_conn():
    plc = client.Client()
    plc.set_connection_type(3)
    plc.connect('192.168.110.248', 0, 1)
    state = plc.get_connected()  # 连接是否成功 true / false
    if state:
        print('连接 PLC 成功')
        return plc
    print('连接 PLC 失败')
    return None


def close_plc_conn(plc_conn=None):
    if not plc_conn:
        return
    plc_conn.disconnect()  # 断开连接
    plc_conn.destroy()  # 销毁客户端对象，该对象可用于重新连接


# 读取 V1010.2 的布尔值
def read_bit(plc_conn, byte_index, bit_index):
    try:
        data = plc_conn.read_area(Area.DB, DB_NUMBER, byte_index, 1)  # 读取 1 个字节
        print(f'读取到的原始字节: {data}')
        value = util.get_bool(data, 0, bit_index)  # 提取指定 bit 位
        print(f'[READ] V1010.2 = {value}')
        return value
    except Exception as e:
        print(f'[ERROR] 读取失败: {e}')
        return None


# 修改 V1010.2 的布尔值
def write_bit(plc_conn, byte_index, bit_index, value):
    try:
        data = plc_conn.read_area(Area.DB, DB_NUMBER, byte_index, 1)
        print(f'原始字节数据: {data}')

        # 修改指定 bit 的值
        util.set_bool(data, 0, bit_index, value)
        print(f'修改后的字节数据: {data}')

        # 将修改后的数据写回 PLC
        plc_conn.write_area(Area.DB, DB_NUMBER, byte_index, data)
        print(f'[WRITE] V1010.2 设置为 {value}')
    except Exception as e:
        print(f'[ERROR] 写入失败: {e}')


# 读取 VD590（DB1.DBD590）的双字（DWord）值 read_dword(opc, 590)
def read_dword(plc_conn, byte_index):
    data = plc_conn.read_area(Area.DB, DB_NUMBER, byte_index, 4)  # 读取 4 个字节
    value = util.get_dword(data, 0)  # 从字节数据中提取双字（DWord）整数 从第0个字节开始
    return value  # int


def run():
    plc_conn = get_plc_conn()
    try:
        read_data = read_bit(plc_conn, BYTE_INDEX, BIT_INDEX)
        print(f'aaa - {read_data}')

        # write_bit(plc_conn, BYTE_INDEX, BIT_INDEX, True)
        # write_bit(plc_conn, BYTE_INDEX, BIT_INDEX, False)
        print('=====================================')

        # 再次读取以确认
        # read_bit(plc_conn, BYTE_INDEX, BIT_INDEX)

        data_590 = read_dword(plc_conn, 590)
        print(data_590)
    finally:
        close_plc_conn(plc_conn)


if __name__ == '__main__':
    run()
