import json
import datetime
import os
import pdb
import math
import globals
# 保存所有边的长度
# edge_lengths = {}
# # 保存所有节点属性：任务点、途经点、充电点...
# node_attributes = {}

# # 1:pass; 0: wait
# control_instructions = {
#     "AGV001": 1,
#     "AGV002": 0,
#     "AGV003": 1,
#     "AGV004": 0,
# }


# def update_graphs(graph_data):
#     global edge_lengths, node_attributes
#     for line in graph_data['data']["lineList"]:
#         line_name = line["lineName"]
#         line_length = line["lineLength"]
#         edge_lengths[line_name] = line_length
#     for node in graph_data['data']['nodeList']:
#         node_name = node['instanceName']
#         node_class = node['className']
#         node_attributes[node_name] = node_class


# 模拟AGV运行
# utils中直接运行，传入的是globals的Edge_info
def update_agv(agv_original_data, control_commands, update_time_interval, edges_dict, nodes_dict):
    # pdb.set_trace()
    agv_data = agv_original_data['agvList']
    for agv_id in control_commands.keys():
        pos_info = agv_data[agv_id]['posInfo']
        status_info = agv_data[agv_id]['statusInfo']
        order_info = agv_data[agv_id]['orderInfo']
        battery_info = agv_data[agv_id]['batteryInfo']

        if control_commands[agv_id] == 1:
            status_info['status'] = 1
            edge_id = pos_info["edgeId"]
            # 获取AGV当前位置
            # current_pos = pos_info["posPercent"] * edge_lengths[edge_id]
            edge_length = edges_dict[edge_id].length
            current_pos = pos_info["posPercent"] * edge_length
            # 计算AGV移动的距离
            move_speed = edges_dict[edge_id].speed
            # move_distance = status_info["speed"] * update_time_interval
            move_distance = move_speed * update_time_interval
            # 计算AGV移动后的位置
            new_pos = min(current_pos + move_distance, edge_length)

            # 如果AGV到达了边的终点，更新起点和终点
            if new_pos == edge_length:
                current_arrive_node = order_info['siteList'].pop(0)
                status_info['waitTime'] = order_info['waitTimeList'].pop(0)
                status_info['waitCounter'] = math.ceil(status_info['waitTime'] / globals.UPDATE_TIME_INTERVAL)

                if current_arrive_node != pos_info['endNode']:
                    print(f"当前AGV:{agv_id}已经到达边的终点，但与endNode不一致，请检查代码！")

                # 如果列表中还有数据，说明AGV还没有运行结束，还需要继续处理！
                if agv_data[agv_id]['orderInfo']['siteList']:
                    status_info['lastNode'] = pos_info['startNode']
                    pos_info['startNode'] = pos_info['endNode']
                    pos_info['endNode'] = order_info['siteList'][0]
                    pos_info['posPercent'] = 0

                    try:
                        status_info['nextNode'] = order_info['siteList'][1]
                    except IndexError:
                        status_info['nextNode'] = None
                    if status_info['lastNode'] is not None:
                        status_info['lastEdge'] = f"{status_info['lastNode']}-{pos_info['startNode']}"
                    else:
                        status_info['lastEdge'] = None
                    pos_info['edgeId'] = f"{pos_info['startNode']}-{pos_info['endNode']}"
                    if status_info['nextNode'] is not None:
                        status_info['nextEdge'] = f"{pos_info['endNode']}-{status_info['nextNode']}"
                    else:
                        status_info['nextEdge'] = None

                    if status_info['waitCounter'] > 0:
                        status_info['status'] = 2

                # 列表为空，证明AGV 已经到达终点
                else:
                    if status_info['waitCounter'] > 0:
                        status_info['status'] = 2
                    else:
                        status_info['status'] = 0
                    status_info['lastNode'] = pos_info['startNode']
                    status_info['lastEdge'] = pos_info['edgeId']
                    pos_info['startNode'] = pos_info['endNode']
                    pos_info['edgeId'] = None
                    pos_info['endNode'] = None
                    pos_info['posPercent'] = 0
                    # continue
            # 如果没有到达终点，仅更新位置百分比，状态信息和订单信息不变
            else:
                pos_info['posPercent'] = round(new_pos / edge_length, 2)

        # 控制指令为0，命令该AGV等待，位置数据不发生变化，状态置为等待状态
        else:
            if status_info['status'] == 1:
                status_info['status'] = 4
            if status_info['status'] == 2:
                status_info['waitCounter'] -= 1
            # if status_info['waitCounter'] == 0 and pos_info["edgeId"] is None:
            if status_info['waitCounter'] == 0:
                # 起始点是任务点：
                if pos_info['endNode'] is not None:
                    status_info['status'] = 1
                else:
                    status_info['status'] = 0
                # if agv_data[agv_id]['orderInfo']['siteList']:
                #     status_info['lastNode'] = pos_info['startNode']
                #     pos_info['startNode'] = pos_info['endNode']
                #     pos_info['endNode'] = order_info['siteList'][0]
                #     pos_info['posPercent'] = 0
                #
                #     try:
                #         status_info['nextNode'] = order_info['siteList'][1]
                #     except IndexError:
                #         status_info['nextNode'] = None
                #     if status_info['lastNode'] is not None:
                #         status_info['lastEdge'] = f"{status_info['lastNode']}-{pos_info['startNode']}"
                #     else:
                #         status_info['lastEdge'] = None
                #     pos_info['edgeId'] = f"{pos_info['startNode']}-{pos_info['endNode']}"
                #     if status_info['nextNode'] is not None:
                #         status_info['nextEdge'] = f"{pos_info['endNode']}-{status_info['nextNode']}"
                #     else:
                #         status_info['nextEdge'] = None
                # else:
                #     status_info['status'] = 0
                #     status_info['lastNode'] = pos_info['startNode']
                #     status_info['lastEdge'] = pos_info['edgeId']
                #     pos_info['startNode'] = pos_info['endNode']
                #     pos_info['edgeId'] = None
                #     pos_info['endNode'] = None
                #     pos_info['posPercent'] = 0

            # continue
    # next_agv_data = {"code": 200, "message": "success", "data": {agv_data}}
    return agv_original_data


def update_agv_socket(agv_original_data, control_commands, update_time_interval, edges_dict, nodes_dict):
    # pdb.set_trace()
    agv_data = agv_original_data['data']['agvList']
    for agv_id in control_commands.keys():
        if control_commands[agv_id] == 1:
            pos_info = agv_data[agv_id]['posInfo']
            status_info = agv_data[agv_id]['statusInfo']
            order_info = agv_data[agv_id]['orderInfo']
            battery_info = agv_data[agv_id]['batteryInfo']

            edge_id = pos_info["edgeId"]
            # 获取AGV当前位置
            # current_pos = pos_info["posPercent"] * edge_lengths[edge_id]
            edge_length = edges_dict[edge_id]
            current_pos = pos_info["posPercent"] * edge_length
            # 计算AGV移动的距离
            move_distance = status_info["speed"] * update_time_interval
            # 计算AGV移动后的位置
            new_pos = min(current_pos + move_distance, edge_length)

            # 如果AGV到达了边的终点，更新起点和终点
            if new_pos == edge_length:
                current_arrive_node = agv_data[agv_id]['orderInfo']['siteList'].pop(0)
                if current_arrive_node != pos_info['endNode']:
                    print(f"当前AGV:{agv_id}已经到达边的终点，但与endNode不一致，请检查代码！")

                if agv_data[agv_id]['orderInfo']['siteList']:
                    # 如果列表中还有数据，说明AGV还没有完成任务，还需要继续处理！之后增加执行任务的逻辑！
                    status_info['lastNode'] = pos_info['startNode']
                    pos_info['startNode'] = pos_info['endNode']
                    pos_info['endNode'] = order_info['siteList'][0]
                    pos_info['posPercent'] = 0

                    try:
                        status_info['nextNode'] = order_info['siteList'][1]
                    except IndexError:
                        status_info['nextNode'] = None
                    if status_info['lastNode'] is not None:
                        status_info['lastEdge'] = f"{status_info['lastNode']}-{pos_info['startNode']}"
                    else:
                        status_info['lastEdge'] = None
                    pos_info['edgeId'] = f"{pos_info['startNode']}-{pos_info['endNode']}"
                    if status_info['nextNode'] is not None:
                        status_info['nextEdge'] = f"{pos_info['endNode']}-{status_info['nextNode']}"
                    else:
                        status_info['nextEdge'] = None

                else:
                    # 列表为空，证明AGV 已经到达终点，之后修改任务逻辑，先把状态置为0（空闲）
                    status_info['status'] = 0
                    status_info['lastNode'] = pos_info['startNode']
                    status_info['lastEdge'] = pos_info['edgeId']
                    pos_info['startNode'] = pos_info['endNode']
                    pos_info['edgeId'] = None
                    pos_info['endNode'] = None
                    pos_info['posPercent'] = 0
                    continue
            # 如果没有到达终点，仅更新位置百分比，状态信息和订单信息不变
            else:
                pos_info['posPercent'] = round(new_pos / edge_length, 2)

        # 控制指令为0，命令该AGV等待，位置数据不发生变化，状态置为等待状态
        else:
            if agv_data[agv_id]['statusInfo']['status'] == 1:
                agv_data[agv_id]['statusInfo']['status'] = 4
            continue
    # next_agv_data = {"code": 200, "message": "success", "data": {agv_data}}
    return agv_original_data
# 生成下一个时刻的AGV信息JSON并打印
# next_agv_info = update_agv(agv_data, control_commands)
# print("Next AGV info:", next_agv_info)


# with open("simData/graphdata.json", 'r') as file:
#     graphData = json.load(file)
#     update_graphs(graphData)
#     print("Map update completed!")
#
# with open("AGVSimDataUpdate/agvDynamicData_20240515105455.json") as file:
#     agv_current_data = json.load(file)['data']
#     agv_next_data = update_agv(agv_current_data, control_instructions, update_time_interval=1)
#     outfile_folder = "AGVSimDataUpdate"
#     timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#     outfile_name = f"agvDynamicData_{timestamp}.json"
#     with open(os.path.join(outfile_folder, outfile_name), "w") as outfile:
#         json.dump(agv_next_data, outfile, indent=2)
#     print("AGV next time dynamic data has been generated!")
