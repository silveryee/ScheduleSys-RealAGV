import json
import globals
import agv
import graph
import order
import conflicts
import os
import simScript
import math
import copy
from datetime import datetime


# =============================资源更新================================
# 接收Java后端的AGV初始数据,生成仿真所需初始静态数据，动态数据等到有任务分配和路径规划结果后更新
# def generate_agv_first_initdata(agv_init_data):
#     for agv_vehicle in agv_init_data['agvList'].values():
#         # agv_id = agv_vehicle['agvId']
#         statusInfo = agv_vehicle['statusInfo']
#         orderInfo = agv_vehicle['orderInfo']
#
#         orderInfo['waitTimeList'] = None
#
#         statusInfo['waitTime'] = None
#         statusInfo['waitCounter'] = None
#     return agv_init_data


# 资源更新时全部重新写入，AGV 和地图资源需要一起更新
# 静态更新地图资源(globals.EDGE_INFO, globals.NODE_INFO)，给每个节点和边创建动态监控对象并进行初始化，动态更新通过dynamic_update_agvs_and_resources()来完成
def parse_data_to_init_resources(graph_data, edges_dict, nodes_dict):
    edge_data = graph_data['lineList']
    node_data = graph_data['nodeList']
    area_id = graph_data['areaId']
    graph.Node.setRegion(area_id)
    graph.Edge.setRegion(area_id)
    # 处理节点数据
    for node in node_data:
        node_id = node['instanceName']
        if node_id not in nodes_dict:
            label = node["className"]
            nodes_dict[node_id] = graph.Node(node_id, label)
        else:
            nodes_dict[node_id].label = node["className"]

    # 处理边数据
    # 目前没有处理双向边，接口中的"direction"字段是"bidirection"表明是双向边
    for edge in edge_data:
        edge_id = edge['lineName']
        if edge_id not in edges_dict:
            start_node = edge['lineSource']
            end_node = edge['lineTarget']
            length = edge['lineLength']
            width = edge['width']
            # width = edge['lineWidth']
            speed = edge['maxspeed']
            # speed = edge['lineSpeed']
            label = edge['classType']
            edges_dict[edge_id] = graph.Edge(edge_id, start_node, end_node, length, width, speed, label)
        else:
            edges_dict[edge_id].start_node = edge['lineSource']
            edges_dict[edge_id].end_node = edge['lineTarget']
            edges_dict[edge_id].length = float(edge['lineLength'])
            # edges_dict[edge_id].width = edge['lineWidth']
            edges_dict[edge_id].width = edge['width']
            # edges_dict[edge_id].speed = edge['lineSpeed']
            edges_dict[edge_id].speed = edge['maxspeed']
            edges_dict[edge_id].label = edge['classType']


# 静态更新 AGV 初始信息(globals.AGV_VEHICLES)，创建各个AGV的动态监控对象，等待订单下发后调用dynamic_update_agvs_and_resources进行动态更新
def parse_data_to_init_agvs(agv_init_data, agvs_dict):
    area_id = agv_init_data['areaId']
    agv.AGV.setRegion(area_id)
    agv_data = agv_init_data['agvList']
    for agv_vehicle in agv_data.values():
        agv_id = agv_vehicle['agvId']
        if agv_id not in agvs_dict:
            # 不可修改属性
            length = agv_vehicle['length']
            width = agv_vehicle['width']
            height = agv_vehicle['height']
            agv_type = agv_vehicle['className']

            priority = agv_vehicle['priority']
            status = agv_vehicle['statusInfo']['status']
            speed = agv_vehicle['statusInfo']['speed']
            battery = agv_vehicle['batteryInfo']['batteryLevel']
            posData = agv_vehicle['posInfo']
            agvs_dict[agv_id] = agv.AGV(agv_id, length, width, height, agv_type,
                                        status, speed, battery, priority)
            agvs_dict[agv_id].init_pos(posData)
        else:
            agvs_dict[agv_id].priority = agv_vehicle['priority']
            agvs_dict[agv_id].status = agv_vehicle['statusInfo']['status']
            agvs_dict[agv_id].speed = agv_vehicle['statusInfo']['speed']
            agvs_dict[agv_id].battery = agv_vehicle['batteryInfo']['batteryLevel']
            posData = agv_vehicle['posInfo']
            agvs_dict[agv_id].init_pos(posData)


def init_all_resources(graph_info, agv_info):
    globals.EDGE_INFO = {}
    globals.NODE_INFO = {}
    globals.AGV_VEHICLES = {}
    globals.AGV_CONTROL_CMDS = {}
    globals.ORDER_INFO = {}
    parse_data_to_init_resources(graph_info, globals.EDGE_INFO, globals.NODE_INFO)
    parse_data_to_init_agvs(agv_info, globals.AGV_VEHICLES)


# =============================订单更新================================
# 接收到平台下发的订单后创建订单对象(globals.ORDER_INFO)
def parse_data_to_init_orders(order_init_list, orders_dict):
    # order_init_list = copy.deepcopy(order_list)
    for order_obj in order_init_list:
        order_id = order_obj['orderId']
        if order_id not in orders_dict:
            area_id = order_obj['areaId']
            target_list = order_obj['siteList']
            print(f"正在创建订单对象{order_id}")
            orders_dict[order_id] = order.Order(order_id, area_id, target_list)
        else:
            raise ValueError(f"已存在订单编号{order_id}, 请检查下发订单编号是否唯一!")


# 执行任务分配和路径规划算法后，对订单进行动态更新
def dynamic_update_orders(order_res, orders_dict):
    # order_res = copy.deepcopy(order_res_data)
    for order_res_obj in order_res:
        order_id = order_res_obj['orderId']
        assigned_agv_id = order_res_obj['agvId']
        site_list = order_res_obj['siteList']
        print(f"正在更新订单对象{order_id}")
        order_obj = orders_dict[order_id]
        order_obj.update(assigned_agv_id, site_list)

# 根据AGV实时数据agv_dynamic_data 动态更新全局变量的AGV、Order、节点、边状态
# def dynamic_update_agvs_and_resources(agv_dynamic_data, agvs_dict, edges_dict, nodes_dict, orders_dict,
#                                       safe_vehicle_interval):
#     # 调用动态更新函数之前要保证实时数据中的AGV 以及 地图节点、边已完成静态初始化
#     # 即先调用parse_data_to_update_resources() 和 parse_data_to_update_agvs()
#     for agv_data in agv_dynamic_data['agvList'].values():
#         # 更新AGV的实时状态
#         agvId = agv_data["agvId"]
#         posData = agv_data["posInfo"]
#         statusData = agv_data["statusInfo"]
#         orderData = agv_data["orderInfo"]
#         batteryDate = agv_data["batteryInfo"]
#
#         agv_obj = agvs_dict[agvId]
#         # 增加了两个属性：last_node_id 和 last_edge_id
#         agv_obj.update_status_info(statusData)
#         agv_obj.update_pos_info(posData, edges_dict, safe_vehicle_interval)
#         # update_order_info 中新增了订单结束
#         agv_obj.update_order_info(orderData, orders_dict)
#         agv_obj.update_battery_info(batteryDate)
#
#         # 更新地图节点和资源占用情况:
#         # 更新边属性:occupy_agv_id
#         if agv_obj.last_edge_id is not None:
#             last_edge_id = agv_obj.last_edge_id
#             last_edge_obj = edges_dict[last_edge_id]
#             last_edge_obj.update_occupy_agv(agv_obj, agvs_dict, edges_dict)
#         if agv_obj.current_edge_id is not None:
#             current_edge_id = agv_obj.current_edge_id
#             current_edge_obj = edges_dict[current_edge_id]
#             current_edge_obj.update_occupy_agv(agv_obj, agvs_dict, edges_dict)
#             # 更新节点属性：wait_queue, pass_queue
#             start_node_id = agv_obj.start_node_id
#             start_node = nodes_dict[start_node_id]
#             end_node_id = agv_obj.end_node_id
#             end_node = nodes_dict[end_node_id]
#
#             if agv_obj.start_node_dist > 2 * safe_vehicle_interval:
#                 start_node.remove_agv_from_pass_queue(agvId)
#                 start_node.remove_agv_from_wait_queue(agvId)
#                 start_node.unlock(agvId)
#             else:
#                 start_node.add_agv_to_pass_queue(agvId)
#                 start_node.remove_agv_from_wait_queue(agvId)
#                 # start_node.lock(agvId)
#
#             if agv_obj.end_node_dist > 2 * safe_vehicle_interval:
#                 end_node.add_agv_to_wait_queue(agvId)
#             else:
#                 end_node.remove_agv_from_wait_queue(agvId)
#                 end_node.add_agv_to_pass_queue(agvId)
#         # AGV在节点，且状态非运行时，释放占用资源
#         else:
#             if agv_obj.status not in [1, 2, 4]:
#                 occupy_node_id = agv_obj.start_node_id
#                 occupy_node = nodes_dict[occupy_node_id]
#                 occupy_node.remove_agv_from_pass_queue(agvId)
#                 occupy_node.remove_agv_from_wait_queue(agvId)


def dynamic_update_agvs_and_resources_real_car(agv_dynamic_data, agvs_dict, edges_dict, nodes_dict, orders_dict,
                                               safe_vehicle_interval):
    # 调用动态更新函数之前要保证实时数据中的AGV 以及 地图节点、边已完成静态初始化
    # 即先调用parse_data_to_update_resources() 和 parse_data_to_update_agvs()
    for agv_data in agv_dynamic_data['agvList'].values():
        # 更新AGV的实时状态
        agvId = agv_data["agvId"]
        posData = agv_data["posInfo"]
        statusData = agv_data["statusInfo"]
        orderData = agv_data["orderInfo"]
        batteryDate = agv_data["batteryInfo"]

        agv_obj = agvs_dict[agvId]
        # 增加了两个属性：last_node_id 和 last_edge_id
        agv_obj.update_status_info(statusData)
        agv_obj.update_pos_info(posData, edges_dict, safe_vehicle_interval)
        # update_order_info 中新增了订单结束
        agv_obj.update_order_info(orderData, orders_dict)
        agv_obj.update_battery_info(batteryDate)

        # 更新地图节点和资源占用情况:
        # 更新边属性:occupy_agv_id
        if agv_obj.last_edge_id is not None:
            last_edge_id = agv_obj.last_edge_id
            last_edge_obj = edges_dict[last_edge_id]
            last_edge_obj.update_occupy_agv(agv_obj, agvs_dict, edges_dict)
        if agv_obj.current_edge_id is not None:
            current_edge_id = agv_obj.current_edge_id
            current_edge_obj = edges_dict[current_edge_id]
            current_edge_obj.update_occupy_agv(agv_obj, agvs_dict, edges_dict)
            # 更新节点属性：wait_queue, pass_queue
            start_node_id = agv_obj.start_node_id
            start_node = nodes_dict[start_node_id]
            end_node_id = agv_obj.end_node_id
            end_node = nodes_dict[end_node_id]

            if agv_obj.start_node_dist > 2 * safe_vehicle_interval:
                start_node.remove_agv_from_pass_queue(agvId)
                start_node.remove_agv_from_wait_queue(agvId)
                start_node.unlock(agvId)
            else:
                start_node.add_agv_to_pass_queue(agvId)
                start_node.remove_agv_from_wait_queue(agvId)
                # start_node.lock(agvId)

            if agv_obj.end_node_dist > 2 * safe_vehicle_interval:
                end_node.add_agv_to_wait_queue(agvId)
            else:
                end_node.remove_agv_from_wait_queue(agvId)
                end_node.add_agv_to_pass_queue(agvId)
        # AGV在节点，且状态非运行时，释放占用资源
        else:
            if agv_obj.status not in [1, 2, 4]:
                occupy_node_id = agv_obj.start_node_id
                occupy_node = nodes_dict[occupy_node_id]
                occupy_node.remove_agv_from_pass_queue(agvId)
                occupy_node.remove_agv_from_wait_queue(agvId)

# def dynamic_update_agvs_and_resources_new(agv_dynamic_data, agvs_dict, edges_dict, nodes_dict, orders_dict,
#                                           safe_vehicle_interval):
#     # 调用动态更新函数之前要保证实时数据中的AGV 以及 地图节点、边已完成静态初始化
#     # 即先调用parse_data_to_update_resources() 和 parse_data_to_update_agvs()
#     for agv_data in agv_dynamic_data['agvList'].values():
#         # 更新AGV的实时状态
#         agvId = agv_data["agvId"]
#         posData = agv_data["posInfo"]
#         statusData = agv_data["statusInfo"]
#         orderData = agv_data["orderInfo"]
#         batteryDate = agv_data["batteryInfo"]
#
#         agv_obj = agvs_dict[agvId]
#         # 增加了两个属性：last_node_id 和 last_edge_id
#         agv_obj.update_status_info(statusData)
#         agv_obj.update_pos_info(posData, edges_dict, safe_vehicle_interval)
#         # update_order_info 中新增了订单结束
#         agv_obj.update_order_info(orderData, orders_dict)
#         agv_obj.update_battery_info(batteryDate)
#
#         # 更新地图节点和资源占用情况:
#         # 更新边属性:occupy_agv_id
#         # if agv_obj.last_edge_id is not None:
#         #     last_edge_id = agv_obj.last_edge_id
#         #     last_edge_obj = edges_dict[last_edge_id]
#         #     last_edge_obj.update_occupy_agv(agv_obj, agvs_dict, edges_dict)
#
#         for edge_obj in edges_dict.values():
#             if agvId in edge_obj.occupy_agv_id:
#                 if agv_obj.current_edge_id is not None:
#                     edge_obj.update_occupy_agv(agv_obj, agvs_dict, edges_dict)
#                 else:
#                     edge_obj.occupy_agv_id.remove(agvId)
#                     edge_obj.sort_occupy_agv(agvs_dict)
#
#         if agv_obj.current_edge_id is not None:
#             current_edge_id = agv_obj.current_edge_id
#             current_edge_obj = edges_dict[current_edge_id]
#             current_edge_obj.update_occupy_agv(agv_obj, agvs_dict, edges_dict)
#             # 更新节点属性：wait_queue, pass_queue
#             start_node_id = agv_obj.start_node_id
#             start_node = nodes_dict[start_node_id]
#             end_node_id = agv_obj.end_node_id
#             end_node = nodes_dict[end_node_id]
#
#             if agv_obj.start_node_dist > 2 * safe_vehicle_interval:
#                 start_node.remove_agv_from_pass_queue(agvId)
#                 start_node.remove_agv_from_wait_queue(agvId)
#                 start_node.unlock(agvId)
#             else:
#                 start_node.add_agv_to_pass_queue(agvId)
#                 start_node.remove_agv_from_wait_queue(agvId)
#                 # start_node.lock(agvId)
#
#             if agv_obj.end_node_dist > 2 * safe_vehicle_interval:
#                 end_node.add_agv_to_wait_queue(agvId)
#             else:
#                 end_node.remove_agv_from_wait_queue(agvId)
#                 end_node.add_agv_to_pass_queue(agvId)
#         # AGV在节点，且状态非运行时，释放占用资源
#         else:
#             if agv_obj.status not in [1, 2, 4]:
#                 occupy_node_id = agv_obj.start_node_id
#                 occupy_node = nodes_dict[occupy_node_id]
#                 occupy_node.remove_agv_from_pass_queue(agvId)
#                 occupy_node.remove_agv_from_wait_queue(agvId)


# 两种冲突监测，同时通过两种冲突检测的AGV可以通行
def check_conflicts(agvs_dict, cmds_dict):
    node_agvs_cmds = {}
    edge_agvs_cmds = {}
    # 根据globals.AGV_VEHICLES初始化：只管控处于1、2、4状态的车辆，初始状态都为0
    for agv_obj in agvs_dict.values():
        if agv_obj.status in [1, 2, 4]:
            node_agvs_cmds[agv_obj.id] = 1
            edge_agvs_cmds[agv_obj.id] = 1
        else:
            node_agvs_cmds[agv_obj.id] = 0
            edge_agvs_cmds[agv_obj.id] = 0

    conflicts.solve_node_conflicts(globals.AGV_VEHICLES, globals.NODE_INFO, globals.EDGE_INFO,
                                   node_agvs_cmds, globals.SAFE_VEHICLE_INTERVAL)
    conflicts.solve_edge_conflicts(globals.AGV_VEHICLES, globals.EDGE_INFO, edge_agvs_cmds,
                                   globals.SAFE_VEHICLE_INTERVAL)
    for agv_id in node_agvs_cmds.keys():
        if node_agvs_cmds[agv_id] == 1 and edge_agvs_cmds[agv_id] == 1:
            cmds_dict[agv_id] = 1
        else:
            cmds_dict[agv_id] = 0


def traffic_control(agv_dynamic_data, graph_data=None, agv_init_data=None, init_flag=False):
    # 资源更新
    if init_flag:
        init_all_resources(graph_data, agv_init_data)
    #
    # dynamic_update_agvs_and_resources(agv_dynamic_data, globals.AGV_VEHICLES, globals.EDGE_INFO,
    #                                   globals.NODE_INFO, globals.ORDER_INFO, globals.SAFE_VEHICLE_INTERVAL)

    dynamic_update_agvs_and_resources_real_car(agv_dynamic_data, globals.AGV_VEHICLES, globals.EDGE_INFO,
                                               globals.NODE_INFO, globals.ORDER_INFO, globals.SAFE_VEHICLE_INTERVAL)

    # ========================调试代码=====================================
    print("="*50, "冲突检测和交通管制", "="*50)
    for node_id, node_obj in globals.NODE_INFO.items():
        if node_obj.pass_queue:
            print(f"{node_id} pass queue is not None:{node_obj.pass_queue}")
        if node_obj.wait_queue:
            print(f"{node_id} wait queue is not None:{node_obj.wait_queue}")
    print("*"*50)

    for edge_id, edge_obj in globals.EDGE_INFO.items():
        if edge_obj.occupy_agv_id:
            print(f"AGV in {edge_id}: {edge_obj.occupy_agv_id} ")
    print("*"*50)

    # ========================调试结束===============================================

    # 冲突检测解决
    # check_conflicts(globals.AGV_VEHICLES, globals.AGV_CONTROL_CMDS)
    # print("*"*50)
    # print(f"控制指令(0:等待,1:通行)：{globals.AGV_CONTROL_CMDS}")
    # print("=========================================================================")
    globals.show_agv_info()
    print("="*50, "冲突检测和交通管制结束", "="*50)
    # return globals.AGV_CONTROL_CMDS


# 从AGV动态实时数据的json中提取位置相关信息返回给Topo展示
def generate_agv_display_result(agv_dynamic_data, cmds):
    # data = json.load(agv_dynamic_data)
    agvPosRes = []
    areaId = agv_dynamic_data['areaId']
    # print(areaId)
    # areaId = 19
    for agv_data in agv_dynamic_data['agvList'].values():
        # 更新AGV的实时状态
        agvId = agv_data["agvId"]
        cmd = cmds[agvId]
        posInfo = agv_data["posInfo"]
        statusInfo = agv_data["statusInfo"]
        if posInfo["endNode"] is not None:
            source = posInfo["startNode"]
            target = posInfo["endNode"]
            percent = posInfo["posPercent"]
        else:
            source = statusInfo["lastNode"]
            target = posInfo["startNode"]
            percent = 1

        if source is None or target is None:
            continue
        # areaId = agv_data["posInfo"]["areaId"]
        result = {
            "areaId": areaId,
            "agvId": str(agvId),
            "source": str(source),
            "target": str(target),
            "percent": str(percent),
            "cmd": str(cmd)
        }
        agvPosRes.append(result)
    agvPosJson = json.dumps(agvPosRes, indent=4)
    return agvPosJson


# 返回Java后端订单分配和路径规划结果
def generate_order_path_schedule_res(input_data):
    # res = {"Topic": "scheduled_order",
    #        "data": input_data}
    resJson = json.dumps(input_data, indent=4)
    with open("orderRes.json", 'w', encoding='utf-8') as f:
        json.dump(input_data, f, ensure_ascii=False)
    return resJson


# 当有新订单时，需要根据任务分配和路径规划结果生成新的仿真数据，保存未更新订单的车辆状态数据，添加收到新订单的车辆数据
def generate_agv_first_simdata(agv_init_data, mission_response, ):
    for mission_and_path_result in mission_response:
        agv_id = mission_and_path_result['agvId']
        posInfo = agv_init_data['agvList'][agv_id]['posInfo']
        statusInfo = agv_init_data['agvList'][agv_id]['statusInfo']
        orderInfo = agv_init_data['agvList'][agv_id]['orderInfo']

        # 更新订单信息
        orderInfo['orderID'] = mission_and_path_result['orderId']
        # orderInfo['targetList'] = mission_and_path_result['targetList']
        # orderInfo['siteList'] = mission_and_path_result['siteList']
        orderInfo['targetList'] = globals.ORDER_INFO[orderInfo['orderID']].target_list
        # orderInfo['siteList'] = globals.ORDER_INFO[orderInfo['orderID']].site_list
        # orderInfo['waitTimeList'] = globals.ORDER_INFO[orderInfo['orderID']].wait_time_list
        orderInfo['siteList'] = globals.ORDER_INFO[orderInfo['orderID']].site_list.copy()
        orderInfo['waitTimeList'] = globals.ORDER_INFO[orderInfo['orderID']].wait_time_list.copy()
        # AGV 初始位置在节点：
        if posInfo['edgeId'] is None:
            if orderInfo['siteList'][0] != posInfo['startNode']:
                print("当前AGV位置处于节点，路径规划结果不包含该节点，请检查代码！")
            # 更新位置信息
            orderInfo['siteList'].pop(0)
            posInfo['endNode'] = orderInfo['siteList'][0]
            posInfo['edgeId'] = f"{posInfo['startNode']}-{posInfo['endNode']}"
            posInfo['posPercent'] = 0

            try:
                statusInfo['nextNode'] = orderInfo['siteList'][1]
                statusInfo['nextEdge'] = f"{posInfo['endNode']}-{statusInfo['nextNode']}"
            except IndexError:
                statusInfo['nextNode'] = None
                statusInfo['nextEdge'] = None

            statusInfo['waitTime'] = orderInfo['waitTimeList'].pop(0)
            statusInfo['waitCounter'] = math.ceil(statusInfo['waitTime'] / globals.UPDATE_TIME_INTERVAL)
            # 一个节点可能对应多条边，根据路径规划结果给出所在边，更新位置信息
            # 起点不是任务点，不需要等待
            if statusInfo['waitCounter'] == 0:
                # 更新状态信息：
                statusInfo['status'] = 1
            # 起点是任务点，需要等待执行任务
            else:
                statusInfo['status'] = 2
        # 说明 AGV 初始位置在边上：
        else:
            statusInfo['status'] = 1
            try:
                statusInfo['nextNode'] = orderInfo['siteList'][1]
                statusInfo['nextEdge'] = f"{posInfo['endNode']}-{statusInfo['nextNode']}"
            except IndexError:
                statusInfo['nextNode'] = None
                statusInfo['nextEdge'] = None
    return agv_init_data


def check_region(region_id):
    if agv.AGV.getRegion() == region_id and graph.Edge.getRegion() == region_id and graph.Node.getRegion() == region_id:
        return True
    else:
        print(f"当前上报信息的AGV与地图所属区域不一致！")
        print(f"当前上报信息的 AGV 所属区域为{region_id}")
        print(f"初始化地图所属区域为{graph.Edge.getRegion()}")
        print(f"初始化AGV所属区域为{agv.AGV.getRegion()}")
        return False


def append_timestamp_to_filename(filename):
    # 获取当前时间
    now = datetime.now()
    # 将时间格式化为字符串，这里使用的是ISO8601格式，可以自定义
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    # 分割文件名和扩展名
    base_name, ext = filename.rsplit('.', 1)
    # 重新组合文件名，加上时间戳
    new_filename = f"{base_name}_{timestamp}.{ext}"
    return new_filename


if __name__ == "__main__":
    # with open("agvSimData/agvDynamicData.json", 'r') as file:
    #     agv_dynamic_data = json.load(file)
    # graphdata_path = "graphdata.json"
    # agv_init_data_path = "agvInitStaticData.json"
    # traffic_control(agv_dynamic_data, graphdata_path, agv_init_data_path, init_flag=1)
    graphdata_path = "simData/simData02/graphdata.json"
    agv_init_static_data_path = "simData/simData02/agvInitStaticData.json"
    mission_response_path = "simData/simData02/missionResponse.json"
    agv_dynamic_data_path = "agvDynamicData"
    agv_dynamic_data_filename = "agvInitDynamicData.json"
    init_flag = 1

    with open(graphdata_path, 'r') as file:
        graphdata = json.load(file)

    with open(agv_init_static_data_path, 'r') as file:
        agv_init_static_data = json.load(file)

    if init_flag:
        init_all_resources(graphdata, agv_init_static_data)

    with open(mission_response_path, 'r') as file:
        response = json.load(file)

    agv_init_dynamic_data = generate_agv_first_simdata(agv_init_static_data, response, )
    with open(os.path.join(agv_dynamic_data_path, agv_dynamic_data_filename), "w") as outfile:
        json.dump(agv_init_dynamic_data, outfile, indent=2)
    print("AGV init dynamic data has been generated!")
    print("=" * 100)
    for index in range(1, 31):
        if index == 1:
            traffic_control(agv_init_dynamic_data, graphdata, agv_init_static_data, init_flag=False)
            agv_next_time_data = simScript.update_agv(agv_init_dynamic_data, globals.AGV_CONTROL_CMDS,
                                                      update_time_interval=1,
                                                      edges_dict=globals.EDGE_INFO, nodes_dict=globals.NODE_INFO)
            outfile_name = f"agvDynamicData_{index}.json"
            with open(os.path.join(agv_dynamic_data_path, outfile_name), "w") as outfile:
                json.dump(agv_next_time_data, outfile, indent=2)
            print(f"AGV next {index} time dynamic data has been generated!")
            print("=" * 100)
        else:
            input_file_name = f"agvDynamicData_{index - 1}.json"
            with open(os.path.join(agv_dynamic_data_path, input_file_name), "r") as file:
                agv_old_data = json.load(file)
            traffic_control(agv_old_data, graphdata, agv_init_static_data, init_flag=False)
            agv_new_data = simScript.update_agv(agv_old_data, globals.AGV_CONTROL_CMDS, update_time_interval=1,
                                                edges_dict=globals.EDGE_INFO, nodes_dict=globals.NODE_INFO)
            outfile_name = f"agvDynamicData_{index}.json"
            with open(os.path.join(agv_dynamic_data_path, outfile_name), "w") as outfile:
                json.dump(agv_new_data, outfile, indent=2)
            print(f"AGV next '{index}' time dynamic data has been generated!")
            print("=" * 100)
