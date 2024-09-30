import globals
import eventlet
import eventlet.wsgi
# # 使用 monkey.patch_all() 来修改标准库使其与 gevent 兼容
# monkey.patch_all()
import socketio
import queue
import threading
import utils
import json
import simScript
import pdb

# 仿真脚本作为函数直接调用，运行之后一直有数据发送，死循环，注意socket_flag = False
# 创建一个 Socket.IO 服务器实例
sio = socketio.Server(async_mode='eventlet', cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

# 创建队列
# 经过交管算法处理后的数据，处理格式后发送给拓扑图
send_queue = queue.Queue(10000)
agv_dynamic_data_queue = queue.Queue(10000)
order_res_queue = queue.Queue(10000)

# pool_1：process_data, send_data
pool_1 = eventlet.GreenPool(5)
# pool_2: monitor_order
pool_2 = eventlet.GreenPool(5)

# 控制所有线程执行标志位，当资源更新时，需要重启所有线程
running_flag = True
# 控制订单更新线程执行标志位
order_update_flag = False

socket_flag = False


def process_data():
    global running_flag
    while running_flag and not order_update_flag:
        if not agv_dynamic_data_queue.empty():
            agv_dynamic_data = agv_dynamic_data_queue.get()
            # 交管处理数据，生成调度指令
            cmds = utils.traffic_control(agv_dynamic_data)
            send_queue.put((agv_dynamic_data, cmds))
        eventlet.sleep(globals.UPDATE_TIME_INTERVAL)  # 使用 gevent.sleep() 代替 sio.sleep()


def send_data():
    global running_flag
    while running_flag and not order_update_flag:
        if not send_queue.empty():
            data = send_queue.get()
            agv_dynamic_data = data[0]
            cmds = data[1]
            # 提取拓扑图所需 AGV 位置信息
            topo_result = utils.generate_agv_display_result(agv_dynamic_data, cmds)
            # topo_result_json = json.dumps(topo_result)
            sio.emit('response', topo_result, namespace='/topo')

            # sio.emit('response', topo_result, namespace='/')

            # sio.emit('simScriptRes', sim_result, namespace='/simScript')
            agv_new_data = simScript.update_agv(agv_dynamic_data, cmds,
                                                update_time_interval=globals.UPDATE_TIME_INTERVAL,
                                                edges_dict=globals.EDGE_INFO, nodes_dict=globals.NODE_INFO)
            agv_dynamic_data_queue.put(agv_new_data)
        # gevent.sleep(1)  # 使用 gevent.sleep() 代替 sio.sleep()
        eventlet.sleep(globals.UPDATE_TIME_INTERVAL)  # 使用 gevent.sleep() 代替 sio.sleep()


def monitor_order():
    # 监听订单结果队列，暂停process和send线程，保存未更新订单的AGV位置，更改有新订单的AGV位置，生成agv_init_dynamic_data, 再重启线程
    global running_flag
    while running_flag:
        if not order_res_queue.empty():
            # 线程暂停！
            global order_update_flag, pool_1
            print("收到新订单")
            print("正在等待当前处理数据和发送数据线程结束...")
            print(pool_1.running())
            print(pool_1.coroutines_running)
            print(pool_1.waiting())
            print("*" * 100)
            order_update_flag = True
            pool_1.waitall()
            print("当前处理和发送线程已结束，正在更新仿真数据...")
            print("=======================Test=========================!")
            print(agv_dynamic_data_queue.qsize())
            print(send_queue.qsize())

            new_order = order_res_queue.get()
            print(new_order)
            if not send_queue.empty():
                agv_init_static_data = send_queue.get()
            else:
                agv_init_static_data = agv_dynamic_data_queue.get()

            print(agv_init_static_data)
            # pdb.set_trace()
            agv_init_dynamic_data = utils.generate_agv_first_simdata(agv_init_static_data, new_order)
            print(agv_init_dynamic_data)
            print("正在清理队列数据...")
            agv_dynamic_data_queue.queue.clear()
            send_queue.queue.clear()
            print("队列清理完毕...")

            # 复位控制线程执行的flag，重启线程
            order_update_flag = False
            agv_dynamic_data_queue.put(agv_init_dynamic_data)

            pool_1.spawn_n(send_data)
            pool_1.spawn_n(process_data)
            print("Restart completed!.")
            print("重启后：当前所有线程的名称：")
            print(pool_1.running())
            print(pool_1.coroutines_running)
            print(pool_1.waiting())
            print("*" * 100)
        eventlet.sleep(globals.UPDATE_TIME_INTERVAL)


# 监听后端接口，获取更新的地图资源以及AGV初始位置数据
def get_init_data(init_data=None):
    # 获取java后端的资源及AGV初始位置数据init_data，之后替换
    # 与浩明确认通信方式后再写这部分代码对java后端进行监听
    graphdata_path = "../simData/simData02/graphdata.json"
    agv_init_static_data_path = "../simData/simData02/agvInitStaticData.json"
    mission_response_path = "../simData/simData02/missionResponse.json"

    with open(graphdata_path, 'r') as file:
        graphdata = json.load(file)
    with open(agv_init_static_data_path, 'r') as file:
        agv_init_static_data = json.load(file)

    utils.init_all_resources(graphdata, agv_init_static_data, socket_flag=socket_flag)
    with open(mission_response_path, 'r') as file:
        response = json.load(file)

    agv_init_dynamic_data = utils.generate_agv_first_simdata(agv_init_static_data, response, )
    # with open(os.path.join(agv_dynamic_data_path, agv_dynamic_data_filename), "w") as outfile:
    #     json.dump(agv_init_dynamic_data, outfile, indent=2)
    # print("AGV init dynamic data has been generated!")
    # print("="*100)
    agv_dynamic_data_queue.put(agv_init_dynamic_data)


def print_agv_info():
    for agv_vehicle in globals.AGV_VEHICLES.values():
        agv_vehicle.info()


def restart_all_coroutines():
    # global running_flag, coroutine_list
    global running_flag, pool_1, pool_2
    print("Restarting...")
    print("重启前：当前所有线程的名称：")
    # for th in threading.enumerate():
    #     print(th.name)
    print(pool_1.running())
    print(pool_1.coroutines_running)
    print(pool_1.waiting())
    print("*" * 50)
    print(pool_2.running())
    print(pool_2.coroutines_running)
    print(pool_2.waiting())
    print("*" * 100)

    print_agv_info()

    # 等待当前线程结束
    running_flag = False
    # for t in coroutine_list:
    #     t.wait()
    pool_1.waitall()
    pool_2.waitall()
    # 清空队列
    agv_dynamic_data_queue.queue.clear()
    send_queue.queue.clear()
    order_res_queue.queue.clear()
    # 复位控制线程执行的flag，重启线程
    running_flag = True
    # 重新启动生产者和消费者线程
    # send_coroutine = eventlet.spawn(send_data)
    # coroutine_list.append(send_coroutine)
    # process_coroutine = eventlet.spawn(process_data)
    # coroutine_list.append(process_coroutine)
    pool_1.spawn_n(send_data)
    pool_1.spawn_n(process_data)
    pool_2.spawn_n(monitor_order)

    print("Restart completed!.")
    print("重启后：当前所有线程的名称：")
    # for th in threading.enumerate():
    #     print(th.name)
    print(pool_1.running())
    print(pool_1.coroutines_running)
    print(pool_1.waiting())
    print("*" * 50)
    print(pool_2.running())
    print(pool_2.coroutines_running)
    print(pool_2.waiting())
    print("*" * 100)

    print_agv_info()


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


@sio.on('connect', namespace='/order')
def connect(sid, environ):
    print('Order Client connected:', sid)


#
# @sio.on('connect', namespace='/simScript')
# def connect(sid, environ):
#     print('Simulation Script Client connected:', sid)


# java后端进行地图或AGV等静态资源更新事件
@sio.on('restart', namespace='/update')
def restart(sid, data):
    restart_all_coroutines()
    # 地图和AGV初始化
    get_init_data(data)


# 测试，模拟订单下发更新
# java后端进行地图或AGV等静态资源更新事件
@sio.on('order_update', namespace='/order')
def restart(sid, data):
    print("收到订单更新！")
    order_data = json.loads(data)
    order_res_queue.put(order_data)


# 运行服务器
if __name__ == '__main__':
    pool_1.spawn_n(send_data)
    pool_1.spawn_n(process_data)
    pool_2.spawn_n(monitor_order)

    listen_fd = eventlet.listen(('10.9.58.239', 5000))
    run_server(listen_fd)
