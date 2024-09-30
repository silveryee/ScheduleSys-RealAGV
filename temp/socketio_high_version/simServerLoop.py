import pdb
import gevent
from gevent import monkey
import globals
# 使用 monkey.patch_all() 来修改标准库使其与 gevent 兼容
monkey.patch_all()
import socketio
import queue
import threading
import utils
import json
import simScript

# 仿真脚本作为函数直接调用，运行之后一直有数据发送，死循环，注意socket_flag = False
# 创建一个 Socket.IO 服务器实例
sio = socketio.Server(async_mode='gevent')
# 创建队列
send_queue = queue.Queue(10000)
agv_dynamic_data_queue = queue.Queue(10000)

threading_list = []
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
        gevent.sleep(1)


def send_data():
    global running_flag
    while running_flag:
        if not send_queue.empty():
            data = send_queue.get()
            agv_dynamic_data = data[0]
            cmds = data[1]
            # 提取拓扑图所需 AGV 位置信息
            topo_result = utils.generate_agv_display_result(agv_dynamic_data)
            # topo_result_json = json.dumps(topo_result)
            # sio.emit('response', topo_result, namespace='/topo')
            sio.emit('response', topo_result, namespace='/')
            # sio.emit('simScriptRes', sim_result, namespace='/simScript')
            agv_new_data = simScript.update_agv(agv_dynamic_data, cmds, update_time_interval=1,
                                                edges_dict=glob.EDGE_INFO, nodes_dict=glob.NODE_INFO)
            agv_dynamic_data_queue.put(agv_new_data)
        gevent.sleep(1)  # 使用 gevent.sleep() 代替 sio.sleep()


send_thread = threading.Thread(target=send_data)
threading_list.append(send_thread)
process_thread = threading.Thread(target=process_data)
threading_list.append(process_thread)
send_thread.start()
process_thread.start()


# 监听后端接口，获取更新的地图资源以及AGV初始位置数据
def get_init_data(init_data=None):
    # 获取java后端的资源及AGV初始位置数据init_data，之后替换
    # 与浩明确认通信方式后再写这部分代码对java后端进行监听
    graphdata_path = "../../simData/simData02/graphdata.json"
    agv_init_static_data_path = "../../simData/simData02/agvInitStaticData.json"
    mission_response_path = "../../simData/simData02/missionResponse.json"
    agv_dynamic_data_path = "../../agvDynamicData"
    agv_dynamic_data_filename = "agvInitDynamicData.json"

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
    print("Restarting...")
    print("重启前：当前所有线程的名称：")
    for th in threading.enumerate():
        print(th.name)

    global running_flag, threading_list
    # 等待当前线程结束
    running_flag = False
    for t in threading_list:
        t.join()
    # 清空队列
    agv_dynamic_data_queue.queue.clear()
    send_queue.queue.clear()
    # 复位控制线程执行的flag，重启线程
    running_flag = True
    # 重新启动生产者和消费者线程
    send_thread = threading.Thread(target=send_data)
    threading_list.append(send_thread)
    process_thread = threading.Thread(target=process_data)
    threading_list.append(process_thread)
    send_thread.start()
    process_thread.start()
    print("Restart completed!.")
    print("重启后：当前所有线程的名称：")
    for th in threading.enumerate():
        print(th.name)

    # 地图和AGV初始化
    get_init_data(data)


@sio.on('connect')
def connect(sid, environ):
    print('Default Client connected:', sid)


# @sio.on('connect', namespace='/topo')
# def connect(sid, environ):
#     print('Topo Client connected:', sid)


# 定义 Socket.IO 应用
app = socketio.WSGIApp(sio)

# 打印当前所有线程的名称
print("当前所有线程的名称：")
for thread in threading.enumerate():
    print(thread.name)

# 运行服务器
if __name__ == '__main__':
    from gevent.pywsgi import WSGIServer

    # 使用 gevent 作为 Socket.IO 的后端
    # http_server = WSGIServer(('localhost', 5000), app)
    http_server = WSGIServer(('10.9.58.239', 5000), app)
    http_server.serve_forever()
