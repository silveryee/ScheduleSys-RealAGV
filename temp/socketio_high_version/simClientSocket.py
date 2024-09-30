import pdb

import socketio
import simScript
import queue
import globals

sio = socketio.Client()
# input_queue = queue.Queue(1000)
# output_queue = queue.Queue(1000)


# @sio.on('connect')
# def connect(sid, environ):
#     print('connected:', sid)
namespace = '/simScript'
# @sio.event
# def connect():
#     print('connection established')


# 连接事件处理
@sio.event(namespace=namespace)
def connect():
    print(f"Connected to namespace {namespace}")


@sio.on('simScriptRequest', namespace=namespace)
def process(agv_data, cmds, edge_info, node_info):
    print("Received response:", agv_data)
    print("Received response:", cmds)
    print("Received response:", edge_info)
    print("Received response:", node_info)

    # agv_old_data = data[0]
    # cmds = data[1]
    # agv_new_data = simScript.update_agv(agv_data, cmds, update_time_interval=1,
    #                                     edges_dict=glob.EDGE_INFO, nodes_dict=glob.NODE_INFO)
    # agv_new_data = simScript.update_agv(agv_data, cmds, update_time_interval=1,
    #                                     edges_dict=edge_info, nodes_dict=node_info)
    agv_new_data = simScript.update_agv_socket(agv_data, cmds, update_time_interval=1,
                                               edges_dict=edge_info, nodes_dict=node_info)
    sio.emit('simScriptResult', agv_new_data, namespace=namespace)


@sio.event
def disconnect():
    print('disconnected from server')


sio.connect('http://10.9.58.239:5000')
sio.wait()
