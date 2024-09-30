import queue
import threading
import time
import json
from typing import Dict


# 当前所有AGV的状态字典
# AGV_VEHICLES : Dict[str, 'agv.AGV'] = {}
AGV_VEHICLES = {}
# 静态地图
# STATIC_GRAPH : graph.Graph(data=[])
# 当前地图中所有边的状态字典
# EDGE_INFO : Dict[str, 'graph.Edge'] = {}
EDGE_INFO = {}
# 当前地图所有节点的状态字典
# NODE_INFO : Dict[str, 'graph.Node'] = {}
NODE_INFO = {}
# 订单信息：
# ORDER_INFO : Dict[str, 'order.Order'] = {}
ORDER_INFO = {}
# 数据结构设计，冲突检测结果怎么表示方便，目前未用到
CONFLICTS_INFO = {}
# AGV 控制指令
AGV_CONTROL_CMDS: Dict[str, int] = {}

# 仿真脚本在socket客户端中运行时才用到，自循环版本不需要
EDGE_LENGTHS = {}
NODE_ATTRIBUTES = {}

# 车辆安全间隔(m)
SAFE_VEHICLE_INTERVAL = 0.5
# 时间安全间隔（s）:考虑安全刹车距离，转弯通过路口时间等综合因素设定安全间隔
# 暂时还未用到，后续优化：在预测性检测节点冲突函数中使用：conflicts.check_node_conflicts()
SAFE_TIME_INTERVAL = 5
# 仿真脚本更新间隔(单位：s)，0.2较为合适
UPDATE_TIME_INTERVAL = 0.2

GRAPHDATA = None
AGV_INIT_STATIC_DATA = None
ORDER_RES_QUEUE = queue.Queue(1000)


# 读取数据库，获取agv静态信息，初始化 AGV_VEHICLES
def init_AGV():
    pass


# 读取数据库，获取地图静态信息，初始化 STATIC_GRAPH
def init_GRAPH():
    pass


def init_NODE():
    pass


def init_Edge():
    pass


def show_agv_info():
    for agv_vehicle in AGV_VEHICLES.values():
        print(f"AGV 编号：{agv_vehicle.id}, 当前状态：{agv_vehicle.status}")
