import networkx as nx
import json
from typing import Dict, Any
from networkx import astar_path


class GraphData:
    def __init__(self, graph_data: Dict[str, Any]):
        self.graph_data = graph_data
        self.nodes = []
        self.edges = []
        self.load_graph_data()

    def load_graph_data(self):
        try:
            self.nodes = self.graph_data['nodes']
            self.edges = self.graph_data['edges']
        except KeyError as e:
            raise ValueError(f"Invalid graph data: missing key {e}")


def get_graph_data(graph_data: Dict[str, Any]) -> GraphData:
    return GraphData(graph_data)


def transform_data(json_data):
    # 提取nodes的id
    nodes = [node["instanceName"] for node in json_data["nodeList"]]

    # 提取lines的信息并转换
    links = []
    for line in json_data["lineList"]:
        links.append({
            "start": line["lineSource"],
            "end": line["lineTarget"],
            "lineWidth": line["width"],
            # "cost": line["lineLength"],
            # "cost": line["lineLength"] / line["speedLimit"]
            "cost": line["lineLength"] / line["maxspeed"]
        })

    # 构造data
    data = {
        "nodes": nodes,
        "edges": links
    }

    return data


def get_max_width_for_next_point(sites, next_point, actual_width):
    """
    Updates the actual_width dictionary with container IDs and widths for QH points,
    and removes entries for SH points up to the specified next_point.

    Parameters:
    - waybill (dict): A dictionary containing 'siteList' key with a list of sites.
    - next_point (str): The nodeId to stop processing at.
    - actual_width (dict): A dictionary mapping container ID to width.

    Returns:
    - int: The maximum width among all containers considered.
    """
    # sites = {site['nodeId']: site for site in waybill['siteList']}

    for site in sites:
        node_id = site['nodeId']
        node_type = site['nodeType']

        if node_id == next_point:
            if node_type == "QH":
                container_id = site['containerId']
                # 读取site下container中的width
                container_width = site['container']['width']
                actual_width[container_id] = container_width

            elif node_type == "SH":
                container_id = site['containerId']
                if container_id in actual_width:
                    del actual_width[container_id]

            break

    return max(actual_width.values())


def find_passable_edges(graph_data, max_width):
    edges = graph_data['edges']

    passable_edges = []
    passable_nodes = set()

    for edge in edges:
        if edge['lineWidth'] >= max_width:
            passable_edges.append(edge)
            passable_nodes.add(edge['start'])
            passable_nodes.add(edge['end'])

    return {'nodes': list(passable_nodes), 'edges': passable_edges}


# def plan_path(orderid_data: Dict[str, Any], graph_data: Dict[str, Any], agv_positions: Dict[str, str], agvs_dict) -> str:
def plan_path(orderid_data: Dict[str, Any], graph_data: Dict[str, Any], agv_positions: Dict[str, str], agvs_dict) -> str:
    agv_id = orderid_data["agvId"]
    original_target_list = orderid_data["targetList"].copy()
    # target_list = orderid_data["targetList"]
    target_list = [node["nodeId"] for node in orderid_data["targetList"]]
    target_list_copy = [node["nodeId"] for node in orderid_data["targetList"]].copy()
    if agvs_dict is None:
        agv_contaniner_width = {agv_id: 0.5}
    else:
        agv_contaniner_width = {agv_id: agvs_dict[agv_id].width}
    #

    if not target_list:
        raise ValueError(f"目标列表不能为空 ({agv_id})")

    graph_data_obj = get_graph_data(graph_data)

    # 获取AGV当前位置
    agv_current_position = agv_positions.get(agv_id)
    if agv_current_position is None or agv_current_position not in graph_data_obj.nodes:
        raise ValueError(f"无法找到AGV({agv_id})的当前位置({agv_current_position})在节点列表中")

    # # 创建有向图
    # G = nx.DiGraph()
    # G.add_nodes_from(graph_data_obj.nodes)
    # G.add_weighted_edges_from([(edge['start'], edge['end'], edge['cost']) for edge in graph_data_obj.edges])

    target_list.insert(0, agv_current_position)
    # print(target_list)
    full_path = [target_list[0]]  # 初始化路径为AGV当前位置
    for i in range(1, len(target_list)):
        # 经过的节点列表中
        pass_point = target_list[i-1]
        # print(pass_point)
        next_point = target_list[i]
        # print(next_point)
        agv_actual_width = get_max_width_for_next_point(original_target_list, pass_point, agv_contaniner_width)
        # print(agv_actual_width)
        passable_edges = find_passable_edges(graph_data, agv_actual_width)
        # print(passable_edges)
        graph_data_obj = get_graph_data(passable_edges)

        # 创建有向图
        G = nx.DiGraph()
        G.add_nodes_from(graph_data_obj.nodes)
        G.add_weighted_edges_from([(edge['start'], edge['end'], edge['cost']) for edge in graph_data_obj.edges])

        # next_path = astar_path(G, full_path[-1], next_point, weight="cost")
        # print(next_path)
        next_path = astar_path(G, full_path[-1], next_point)
        # print(next_path)
        if not next_path:
            raise ValueError(f"无法规划从{full_path[-1]}到{next_point}的路径")
        full_path.extend(next_path[1:])  # 添加除了当前节点外的所有节点

    # 构建输出字典并转换为JSON字符串
    result_dict = {
        "orderId": orderid_data["orderId"],
        "areaId": orderid_data.get("areaId"),
        "missionKey": orderid_data["missionKey"],
        "agvId": agv_id,
        "targetList": target_list_copy,
        "siteList": list(map(str, full_path)),
    }

    return result_dict


if __name__ == "__main__":
    order_data_example = {
        "orderId": "00001",
        "areaId": "Area001",
        "missionKey": 1,
        "agvId": "Agv001",
        "targetList": ['QH1', 'SH1', 'LM3'],
    }

    # 读取JSON文件
    with open('topo_map_data2.json', 'r') as file:
        data = json.load(file)
    transformed_data = transform_data(data)
    print(transformed_data)

    agv_positions = {
        "Agv001": "LM1",
        "Agv002": "LM4",
        "Agv003": "LM1",
        "Agv004": "LM2"
    }

    # 需要订单信息，增加"nodeType", "containerId", "container长宽高"
    # 需要AGV信息，AGV ID对应的AGV车体宽度
    # 需要更新agv_contaniner_width
    waybill = {
        "orderId": "00001",
        "areaId": "Area001",
        "createTime": "2024/03/18 14:09",
        "siteList": [
            {
                "nodeId": "LM1",
                "postionX": 190.33,
                "postionY": 270.2,
                "nodeTime": 0,
                "nodeType": "LM",  # 普通点
            },
            {
                "nodeId": "QH1",
                "postionX": 190.33,
                "postionY": 270.2,
                "nodeTime": 0,
                "nodeType": "QH",  # 取货点
                # 增加container ID
                "containerId": "00001-01",
                "container": {
                    "length": 1.5,  # 长
                    "width": 0.8,  # 宽
                    "height": 1.2  # 高
                }
            },
            {
                "nodeId": "LM2",
                "postionX": 190.33,
                "postionY": 270.2,
                "nodeTime": 0,
                "nodeType": "LM",  # 送货点
            },
            {
                "nodeId": "SH1",
                "postionX": 210.55,
                "postionY": 400.8,
                "nodeTime": 20,
                "nodeType": "SH",  # 充电点
                "containerId": "00001-01",
                "container": {
                    "length": 1.5,  # 长
                    "width": 0.8,  # 宽
                    "height": 1.2  # 高
                }
            },
            {
                "nodeId": "LM3",
                "postionX": 250.75,
                "postionY": 450.1,
                "nodeTime": 25,
                "nodeType": "PP"  # 停靠点
            }
        ]
    }

    # # 调用路径规划函数
    # result = plan_path(order_data_example, transformed_data, agv_positions, waybill, agvs_dict)
    # print(result)
