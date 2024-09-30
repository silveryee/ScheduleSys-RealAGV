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

# 仿真脚本作为函数直接调用，运行之后一直有数据发送，死循环，注意socket_flag = False
# 创建一个 Socket.IO 服务器实例
sio = socketio.Server(async_mode='eventlet', cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

# 创建队列
send_queue = queue.Queue(10000)
agv_dynamic_data_queue = queue.Queue(10000)

# coroutine_list = []
pool = eventlet.GreenPool(5)
# 控制处理数据和发送数据的线程执行标志位，
running_flag = True
socket_flag = False


def process_data():
    global running_flag
    while running_flag:
        if not agv_dynamic_data_queue.empty():
            agv_dynamic_data = agv_dynamic_data_queue.get()
            # 交管处理数据，生成调度指令
            cmds = utils.traffic_control(agv_dynamic_data)
            send_queue.put((agv_dynamic_data, cmds))
        eventlet.sleep(globals.UPDATE_TIME_INTERVAL)  # 使用 gevent.sleep() 代替 sio.sleep()


def send_data():
    global running_flag
    while running_flag:
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
            agv_new_data = simScript.update_agv(agv_dynamic_data, cmds, update_time_interval=globals.UPDATE_TIME_INTERVAL,
                                                edges_dict=globals.EDGE_INFO, nodes_dict=globals.NODE_INFO)
            agv_dynamic_data_queue.put(agv_new_data)
        # gevent.sleep(1)  # 使用 gevent.sleep() 代替 sio.sleep()
        eventlet.sleep(globals.UPDATE_TIME_INTERVAL)  # 使用 gevent.sleep() 代替 sio.sleep()


# 监听后端接口，获取更新的地图资源以及AGV初始位置数据
def get_init_data(init_data=None):
    # 获取java后端的资源及AGV初始位置数据init_data，之后替换
    # 与浩明确认通信方式后再写这部分代码对java后端进行监听
    graphdata_path = "../simData/simData02/graphdata.json"
    agv_init_static_data_path = "../simData/simData02/agvInitStaticData.json"
    mission_response_path = "../simData/simData02/missionResponse.json"
    # agv_dynamic_data_path = "agvDynamicData"
    # agv_dynamic_data_filename = "agvInitDynamicData.json"

    with open(graphdata_path, 'r') as file:
        graphdata = json.load(file)
    with open(agv_init_static_data_path, 'r') as file:
        agv_init_static_data = json.load(file)

    # utils.init_all_resources(graphdata, agv_init_static_data)
    utils.init_all_resources(graphdata, agv_init_static_data, socket_flag=socket_flag)
    # 线程资源清理以及重启, 设置一个event触发？

    # 需要清空处理数据队列和发送队列等资源

    # 调用任务分配和路径规划，生成仿真脚本的AGV初始数据
    with open(mission_response_path, 'r') as file:
        response = json.load(file)

    agv_init_dynamic_data = utils.generate_agv_first_simdata(agv_init_static_data, response, )
    # with open(os.path.join(agv_dynamic_data_path, agv_dynamic_data_filename), "w") as outfile:
    #     json.dump(agv_init_dynamic_data, outfile, indent=2)
    # print("AGV init dynamic data has been generated!")
    # print("="*100)
    agv_dynamic_data_queue.put(agv_init_dynamic_data)


@sio.event
def restart(sid, data):
    # global running_flag, coroutine_list
    global running_flag, pool
    print("Restarting...")
    print("重启前：当前所有线程的名称：")
    # for th in threading.enumerate():
    #     print(th.name)
    print(pool.running())
    print(pool.coroutines_running)
    print(pool.waiting())
    print("*"*100)

    # 等待当前线程结束
    running_flag = False
    # for t in coroutine_list:
    #     t.wait()
    pool.waitall()
    # 清空队列
    agv_dynamic_data_queue.queue.clear()
    send_queue.queue.clear()
    # 复位控制线程执行的flag，重启线程
    running_flag = True
    # 重新启动生产者和消费者线程
    # send_coroutine = eventlet.spawn(send_data)
    # coroutine_list.append(send_coroutine)
    # process_coroutine = eventlet.spawn(process_data)
    # coroutine_list.append(process_coroutine)
    pool.spawn_n(send_data)
    pool.spawn_n(process_data)

    print("Restart completed!.")
    print("重启后：当前所有线程的名称：")
    # for th in threading.enumerate():
    #     print(th.name)
    print(pool.running())
    print(pool.coroutines_running)
    print(pool.waiting())
    print("*"*100)
    # 地图和AGV初始化
    get_init_data(data)


@sio.event
def connect(sid, environ):
    print('Default Client connected:', sid)


@sio.on('connect', namespace='/topo')
def connect(sid, environ):
    print('Topo Client connected:', sid)


@sio.on('connect', namespace='/simScript')
def connect(sid, environ):
    print('Simulation Script Client connected:', sid)


def run_server(listen_fd):
    try:
        eventlet.wsgi.server(listen_fd, app)
    except Exception:
        print('Error starting thread.')
        raise SystemExit(1)


# def run_other_threads():
#     # 创建 GreenThread 来运行其他子线程
#     send_coroutine = eventlet.spawn(send_data)
#     coroutine_list.append(send_coroutine)
#     process_coroutine = eventlet.spawn(process_data)
#     coroutine_list.append(process_coroutine)


# 运行服务器
if __name__ == '__main__':
    # from gevent.pywsgi import WSGIServer
    #
    # # 使用 gevent 作为 Socket.IO 的后端
    # # http_server = WSGIServer(('localhost', 5000), app)
    # http_server = WSGIServer(('10.9.58.239', 5000), app)
    # http_server.serve_forever()

    # from flask import Flask
    #
    # flask_app = Flask(__name__)
    #
    # @flask_app.route('/')
    # def index():
    #     return 'SocketIO server is running!'

    # eventlet.wsgi.server(eventlet.listen(('172.30.128.242', 5000)), app)
    pool.spawn_n(send_data)
    pool.spawn_n(process_data)
    listen_fd = eventlet.listen(('10.9.58.239', 5000))
    run_server(listen_fd)





