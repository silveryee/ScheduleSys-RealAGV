import json
import numpy as np
from scipy.optimize import linear_sum_assignment
import networkx as nx
from order_allocation_and_path_planning.topo_transform import transform_data
from order_allocation_and_path_planning.agv_path_planning_width import plan_path
from networkx import astar_path, NetworkXNoPath, NodeNotFound


# 在这个版本中，如果某条路径不可达，将成本设置为一个非常大的数值（例如1e6），确保匈牙利算法不会选择这些不可达的AGV进行匹配。
# 之后，打印所有不可达的AGV和订单对的信息，并继续对可达的AGV和订单进行匹配。最终返回和打印的结果将只包含可达的订单和AGV匹配对。

# 5.3更新：订单返回一个值，如果拿取的订单和所有车都不匹配，那么把这个值保存
# 5.3.1更新，订单返回的不再是ID值，而是不能分配的整个对象
# 5.3.2更新，订单返回的是原始的订单对象，不是路径规划和任务分配的对象
# 5.3.3更新，增加check_order_is_executable()可调用的函数
# 5.3.3.1更新：返回值删除部分内容
# 5.3.4更新：将函数做拆解，拆成2部分并测试结果
# 5.3.5更新：把check_order_is_executable改成入参订单为单个订单而不是列表，输出改成true/false而不是不可达订单列表


def optimize_agv_paths(graphdata, waybills, agv_positions, agvs_dict):
    # 创建有向图并添加边和节点
    graphdata = transform_data(graphdata)
    print(graphdata)
    G = nx.DiGraph()
    # 添加节点到图 G 中
    G.add_nodes_from(graphdata["nodes"])

    # 为每条边添加起始点、终点和权重（如边的代价或距离）
    for edge in graphdata["edges"]:
        G.add_edge(edge["start"], edge["end"], weight=edge["cost"])

    # 将运单转换为订单结构，提取每个订单的 orderId 和相关的站点序列（siteList）
    # orders = [{"orderId": waybill["orderId"], "siteList": [node["nodeId"] for node in waybill["siteList"]]} for waybill
    #           in waybills]
    # 要提取siteList全部信息，路径规划需要站点属性以及容器信息等
    orders = [{"orderId": waybill["orderId"], "siteList": waybill["siteList"]} for waybill in waybills]
    # print("Orders:", orders)
    # 初始化成本矩阵（每个订单与每个 AGV 的代价）以及不可到达的 AGV 和订单配对
    cost_matrix = []
    unreachable_pairs = []

    # 遍历每个订单
    for order in orders:
        # task_sequence = order["siteList"]  # 获取订单的站点序列
        # 修改了原始order的结构，重新获取只包含站点ID的序列
        task_sequence = [node["nodeId"] for node in order["siteList"]]
        order_costs = []  # 用于存储当前订单对于每个 AGV 的成本
        all_unreachable = True  # 标记订单是否对所有 AGV 都不可达

        # 遍历每个 AGV 的位置，计算其从起始位置到订单中各个任务站点的路径成本
        for agv_id, agv_start in agv_positions.items():
            total_cost = 0  # 初始化总成本
            try:
                # 遍历订单的站点序列，逐步计算从 AGV 起始位置到站点的路径
                for i in range(len(task_sequence)):
                    if i == 0:
                        # 第一个站点：从 AGV 的起始位置到第一个站点
                        path = astar_path(G, agv_start, task_sequence[i])
                    else:
                        # 后续站点：从前一个站点到下一个站点
                        path = astar_path(G, task_sequence[i - 1], task_sequence[i])
                    # 累加路径的权重（成本）
                    total_cost += nx.path_weight(G, path, weight='weight')
                # 如果找到路径，将该订单与该 AGV 的成本加入 order_costs 列表
                order_costs.append(total_cost)
                all_unreachable = False  # 标记订单对至少一个 AGV 可达
            except (NetworkXNoPath, NodeNotFound):
                # 如果找不到路径，设定该路径成本为一个很大的值（表示不可达）
                order_costs.append(1e6)
                # 记录不可到达的 AGV 和订单配对
                unreachable_pairs.append((agv_id, order["orderId"]))

        # 将该订单对应的所有 AGV 的成本加入成本矩阵
        cost_matrix.append(order_costs)

    # 使用匈牙利算法（linear_sum_assignment）进行订单和 AGV 的最优分配
    optimized_orders = []
    # 根据成本矩阵获取订单与 AGV 的最优匹配
    order_idx, agv_idx = linear_sum_assignment(cost_matrix)

    # 遍历匹配结果，生成优化后的订单分配列表
    for o, a in zip(order_idx, agv_idx):
        # 仅当分配的成本小于 1e6（即可达路径）时才进行分配
        if cost_matrix[o][a] < 1e6:
            assignment = {
                "orderId": orders[o]["orderId"],  # 订单 ID
                "areaId": waybills[o]["areaId"],  # 订单的区域 ID
                "missionKey": 1,  # 任意任务标识
                "agvId": list(agv_positions.keys())[a],  # 分配的 AGV ID
                "targetList": orders[o]["siteList"]  # 订单目标站点列表
            }
            optimized_orders.append(assignment)

    # 对每个订单执行路径规划并更新结果
    for order in optimized_orders:
        result = plan_path(order, graphdata, agv_positions, agvs_dict)
        # print("")
        if result:
            order.update(result)

    return optimized_orders  # 返回优化后的订单分配列表


def check_order_is_executable(graphdata, waybill, agv_positions):
    """

    :param graphdata: 全局 GRAPHDATA,需要调用 transform_data 函数进行转换
    :param waybill: 单个订单
    :param agv_positions: 空闲 AGV的 ID和位置嵌套字典 {"SIM1":"LM1","SIM2":"LM2"}
    :return:
    """
    # 初始化有向图 G
    # 创建图数据
    graphdata = transform_data(graphdata)
    G = nx.DiGraph()
    G.add_nodes_from(graphdata["nodes"])

    # 为每条边添加起始点、终点和权重（如边的代价或距离）
    for edge in graphdata["edges"]:
        G.add_edge(edge["start"], edge["end"], weight=edge["cost"])

    # 需要遍历 siteList 提取 nodeId
    order = {
        "orderId": waybill["orderId"],
        "siteList": [node["nodeId"] for node in waybill["siteList"]]
    }

    task_sequence = order["siteList"]  # 获取订单的站点序列
    all_unreachable = True  # 标记订单是否对所有 AGV 都不可达

    # 遍历每个 AGV 的位置，计算其从起始位置到订单中各个任务站点的路径成本
    for agv_id, agv_start in agv_positions.items():
        try:
            # 遍历订单的站点序列，逐步计算从 AGV 起始位置到站点的路径
            for i in range(len(task_sequence)):
                if i == 0:
                    path = astar_path(G, agv_start, task_sequence[i])  # 第一个站点
                else:
                    path = astar_path(G, task_sequence[i - 1], task_sequence[i])  # 后续站点
            all_unreachable = False  # 如果找到路径，标记订单可达
            break  # 找到一个可达路径后就不再继续检查其他 AGV
        except (NetworkXNoPath, NodeNotFound):
            continue  # 继续检查其他 AGV

    # 如果订单可达，返回 True，否则返回 False
    return not all_unreachable


if __name__ == '__main__':
    # with open('topo_map_data.json', 'r') as file:
    with open('topo_map_data_unreachable.json', 'r') as file:
        # with open('topo_map_data_indirect.json', 'r') as file:
        data = json.load(file)
    data = transform_data(data)  # transformer去掉data中所有无关的数据，只留下了点和边以及边的代价信息，具备了基本构成图的条件

    print("data transform之后是\n")
    print(data)
    print("transformer完毕")

    with open('order.json', 'r') as file:
        # with open('order_unreachable.json', 'r') as file:
        # with open('order_indirect.json', 'r') as file:
        order_dict = json.load(file)

    # 从字典中提取 AGV 位置信息
    agv_list = order_dict['agv_position']['agvList']
    start_positions = order_dict['agv_position']['startPosition']

    # 创建一个新的字典来存储 AGV 的位置信息
    agv_positions = {agv: position for agv, position in zip(agv_list, start_positions)}

    waybills = [
        {
            "orderId": "00001",
            "areaId": "Area001",
            "createTime": "2024/03/18 14:09",
            "siteList": [
                {"nodeId": "LM1", "postionX": 190.33, "postionY": 270.2, "nodeTime": 0},
                {"nodeId": "LM2", "postionX": 190.33, "postionY": 270.2, "nodeTime": 12}
            ]
        },
        {
            "orderId": "00002",
            "areaId": "Area001",
            "createTime": "2024/03/18 14:09",
            "siteList": [
                {"nodeId": "LM2", "postionX": 190.33, "postionY": 270.2, "nodeTime": 0},
                {"nodeId": "LM1", "postionX": 190.33, "postionY": 270.2, "nodeTime": 12}
            ]
        },
        {
            "orderId": "00003",
            "areaId": "Area001",
            "createTime": "2024/03/18 14:09",
            "siteList": [
                {"nodeId": "LM3", "postionX": 190.33, "postionY": 270.2, "nodeTime": 0},
                {"nodeId": "LM4", "postionX": 190.33, "postionY": 270.2, "nodeTime": 12}
            ]
        }

    ]

    waybill = [
        {
            "orderId": "00001",
            "areaId": "Area001",
            "createTime": "2024/03/18 14:09",
            "siteList": [
                {"nodeId": "LM1", "postionX": 190.33, "postionY": 270.2, "nodeTime": 0},
                {"nodeId": "LM2", "postionX": 190.33, "postionY": 270.2, "nodeTime": 12}
            ]
        }
    ]

    optimized_orders = optimize_agv_paths(data, waybills, agv_positions)

    unassigned_orders = check_order_is_executable(data, waybill, agv_positions)

    print("最终输出结果打印")
    if optimized_orders:
        for order in optimized_orders:
            print(order)

    print(unassigned_orders)
    # if unassigned_orders:
    #     for order in unassigned_orders:
    #         print(order)
