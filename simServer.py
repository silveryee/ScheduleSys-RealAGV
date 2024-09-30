import eventlet
import eventlet.wsgi
import socketio
import queue
import json
import pdb
import os
import pprint

import globals
import utils
from order_allocation_and_path_planning.fastscheduling import optimize_agv_paths, check_order_is_executable


save_file_path = "simData"
resource_save_file = utils.append_timestamp_to_filename("initJavaData.json")
order_save_file = utils.append_timestamp_to_filename("orderJavaData.json")
agv_dynamic_data_save_file = utils.append_timestamp_to_filename("agvDataLog.json")

# 仿真脚本作为函数直接调用，运行之后一直有数据发送，死循环，注意socket_flag = False
sio = socketio.Server(async_mode='eventlet', cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

# 创建队列
# 存放仿真脚本生成的AGV动态数据, (线程process_data)调用交管算法处理，将处理后的数据放入send_queue
agv_dynamic_data_queue = queue.Queue(10000)
#  (线程send_data)按照约定数据格式处理后发送给拓扑图，再调用仿真脚本生成下一份AGV数据放入agv_dynamic_queue，形成闭环
# send_queue = queue.Queue(10000)

# socketio监听订单下发，存储到order_queue，（线程process_order)调用任务分配和路径规划算法处理后放到order_res_queue,
# （线程monitor_order）监听order_res_queue,有数据则同步调用仿真脚本生成新数据
order_queue = queue.Queue(10000)
# order_res_queue = queue.Queue(10000)

# 进程池管理：分开管理的原因是如果地图和AGV初始位置发生变化，所有线程需要重启，如果订单更新，只需要重启 pool1 的处理数据和发送数据的线程
# pool_1：process_data, send_data
pool_1 = eventlet.GreenPool(5)
# pool_2: monitor_order, process_order
pool_2 = eventlet.GreenPool(5)

# 控制所有线程执行标志位，当资源更新时，需要重启所有线程
running_flag = True
# 控制订单更新线程执行标志位
order_update_flag = False
socket_flag = False

# 全局变量，保存地图数据和AGV初始位置，只经过json.load()
GRAPHDATA = None
AGV_INIT_STATIC_DATA = None
# 记录 AGV 动态数据日志，index为序号
index = 0
is_save = False


def process_agv_data():
    global running_flag
    while running_flag and not order_update_flag:
        if not agv_dynamic_data_queue.empty():
            agv_dynamic_data = agv_dynamic_data_queue.get()
            # 更新全局变量AGV、地图资源等
            utils.traffic_control(agv_dynamic_data)
            print_agv_dynamic_info()
            # send_queue.put((agv_dynamic_data, cmds))
            global index
            if is_save:
                with open(os.path.join(save_file_path, agv_dynamic_data_save_file), 'a', encoding='utf-8') as f:
                    f.write(f"Index{index}: \t")
                    json.dump(agv_dynamic_data, f, ensure_ascii=False)
                    f.write(',\n')
                    index = index + 1
        eventlet.sleep(globals.UPDATE_TIME_INTERVAL)  # 使用 gevent.sleep() 代替 sio.sleep()


def process_order():
    # global running_flag, order_queue, order_res_queue
    global running_flag, order_queue
    while running_flag:
        if not order_queue.empty():
            global GRAPHDATA
            # 提取处于空闲状态的AGV的位置
            print("=" * 50, "收到新订单", "=" * 50)
            # available_agv_positions = {agv.id: agv.start_node_id for agv in globals.AGV_VEHICLES.values() if
            #                            agv.status == 0}
            available_agv_positions = {agv.id: agv.pos for agv in globals.AGV_VEHICLES.values() if
                                       agv.status == 0}
            num_available_agvs = len(available_agv_positions)
            print(f"当前有{num_available_agvs}辆空闲状态的AGV:")
            pprint.pprint(available_agv_positions)

            if num_available_agvs == 0:
                print("No available AGVs. Waiting for AGVs to become available.")
                # eventlet.sleep(globals.UPDATE_TIME_INTERVAL)
            else:
                # 取当前下发订单数量和空闲AGV数量的最小值
                # order_batch_size = min(num_available_agvs, order_queue.qsize())
                order_batch_size = 1
                # print("=" * 100)
                # print(
                #     f"订单数量：{order_queue.qsize()}，空闲状态的AGV数量：{num_available_agvs}，当前批次处理订单的数量：{order_batch_size}")

                waybills = []
                for _ in range(order_batch_size):
                    order = order_queue.get()
                    # waybills.append(order)
                    # 写一个 check_order_is_executable()函数，负责检测订单是否可达
                    # order_tolist = [order]
                    if check_order_is_executable(GRAPHDATA, order, available_agv_positions):
                        waybills.append(order)
                    else:
                        print(f"订单编号：{order['orderId']}当前不可执行，已放回队列")
                        order_queue.put(order)
                # print("当前批次处理订单 waybills: ", waybills)
                print("当前处理订单 waybills: ", waybills)

                if waybills:
                    utils.parse_data_to_init_orders(waybills, globals.ORDER_INFO)
                    # print("订单初始化后：")
                    # print_order_info()

                    optimized_orders = optimize_agv_paths(GRAPHDATA, waybills, available_agv_positions, globals.AGV_VEHICLES)
                    print("任务分配和路径规划结果：")
                    for order in optimized_orders:
                        print(f"订单编号：{order['orderId']}, 目标节点：{order['targetList']}, "
                              f"执行AGV编号：{order['agvId']}, 路径规划结果：{order['siteList']}")
                    utils.dynamic_update_orders(optimized_orders, globals.ORDER_INFO)
                    # print("订单更新路径规划结果后：")
                    # print(optimized_orders)
                    # print_order_info()
                    # 根据java后端约定数据格式返回
                    order_path_res = utils.generate_order_path_schedule_res(optimized_orders)

                    sio.emit('scheduled_order', order_path_res, namespace='/update')
                    # order_res_queue.put(optimized_orders)
                    print("=" * 50, "新订单任务分配和路径规划结果已生成", "=" * 50)

            # 和浩明测试一下产生订单结果后就切换线程能否规避订单同时下发来不及更新的bug
            eventlet.sleep(globals.UPDATE_TIME_INTERVAL)

        eventlet.sleep(globals.UPDATE_TIME_INTERVAL)


def print_agv_info():
    for agv_vehicle in globals.AGV_VEHICLES.values():
        agv_vehicle.info()


def print_agv_dynamic_info():
    for agv_vehicle in globals.AGV_VEHICLES.values():
        agv_vehicle.dynamic_info()


def print_order_info():
    for order in globals.ORDER_INFO.values():
        order.info()


def print_graph_info():
    print("地图数据：")
    print("所有边：")
    for edge in globals.EDGE_INFO.values():
        edge.info()
    print("所有节点：")
    for node in globals.NODE_INFO.values():
        print(node.node_id, end=" ")
    print()


# 监听后端接口，获取更新的地图资源以及AGV初始位置数据
def initialize_resources(init_data=None):
    with open(os.path.join(save_file_path, resource_save_file), 'w', encoding='utf-8') as f:
        json.dump(init_data, f, ensure_ascii=False)

    graphdata = init_data['graphData']
    agv_init_static_data = init_data['agvData']
    # 增加任务等待时间相关数据字段，之后如果有新增字段可以在不改变后端数据接口的基础上在该函数中修改
    # 跟后端统一接口后无需调用
    # agv_init_static_data = utils.generate_agv_first_initdata(agv_init_static_data)

    global GRAPHDATA, AGV_INIT_STATIC_DATA
    GRAPHDATA = graphdata
    AGV_INIT_STATIC_DATA = agv_init_static_data
    globals.GRAPHDATA = graphdata
    globals.AGV_INIT_STATIC_DATA = agv_init_static_data

    utils.init_all_resources(graphdata, agv_init_static_data)


def restart_all_coroutines():
    global running_flag, pool_1, pool_2
    # 等待当前线程结束
    running_flag = False
    pool_1.waitall()
    pool_2.waitall()
    # 清空所有数据队列
    agv_dynamic_data_queue.queue.clear()
    # send_queue.queue.clear()
    order_queue.queue.clear()
    # order_res_queue.queue.clear()
    # 复位控制线程执行的flag，重启线程
    running_flag = True
    pool_1.spawn_n(process_agv_data)
    pool_2.spawn_n(process_order)


def run_server(fd):
    try:
        eventlet.wsgi.server(fd, app)
    except Exception:
        print('Error starting thread.')
        raise SystemExit(1)


@sio.on('connect', namespace='/update')
def connect(sid, environ):
    print('Java Client connected:', sid)


@sio.on('connect', namespace='/topo')
def connect(sid, environ):
    print('Topo Client connected:', sid)


# 监听地图或AGV等静态资源更新事件
@sio.on('resource_update', namespace='/update')
def restart(sid, resource_data):
    print("=" * 50, "资源更新", "=" * 50)
    # 重启所有线程
    print("资源更新，正在重启所有线程...")
    init_data = json.loads(resource_data)
    restart_all_coroutines()
    print("所有线程重启完毕！")
    print("正在初始化地图和AGV数据...")
    # 地图和AGV初始化
    initialize_resources(init_data)
    print("地图及AGV初始化完成！")
    print(f"地图数据(类型{type(globals.GRAPHDATA)}):")
    print(globals.GRAPHDATA)
    print_graph_info()
    print("AGV初始位置信息：")
    print_agv_info()
    print("=" * 50, "资源更新完毕", "=" * 50)


# 监听AGV 位置定时上报
@sio.on('agv_data_update', namespace='/update')
def agv_data_update(sid, data):
    if globals.EDGE_INFO and globals.NODE_INFO and globals.AGV_VEHICLES:
        agv_data = json.loads(data)
        # 增加判断区域属性是否一致的逻辑
        area_id = agv_data['areaId']
        if utils.check_region(area_id):
            agv_dynamic_data_queue.put(agv_data)

    else:
        print("等待地图和AGV 初始化数据下发")


# 监听订单更新
@sio.on('order_update', namespace='/update')
def order_update(sid, order):
    order_data = json.loads(order)
    with open(os.path.join(save_file_path, order_save_file), 'a', encoding='utf-8') as f:
        json.dump(order_data, f, ensure_ascii=False)
        f.write(',\n')
    order_queue.put(order_data)


# 运行服务器
if __name__ == '__main__':
    pool_1.spawn_n(process_agv_data)
    pool_2.spawn_n(process_order)

    # listen_fd = eventlet.listen(('10.9.58.239', 5000))
    # listen_fd = eventlet.listen(('172.30.132.78', 5000))
    listen_fd = eventlet.listen(('192.168.2.101', 5000))
    # listen_fd = eventlet.listen(('10.9.58.239', 5000))
    run_server(listen_fd)
