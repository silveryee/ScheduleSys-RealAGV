# import networkx as nx
# import matplotlib.pyplot as plt
#
#
# def draw_graph(nodelist, edgelist):
#     # 创建一个无向图对象
#     G = nx.Graph()
#
#     # 添加节点
#     G.add_nodes_from(nodelist)
#
#     # 添加边
#     G.add_edges_from(edgelist)
#
#     # 绘制图
#     pos = nx.spring_layout(G)  # 使用spring布局算法确定节点的位置
#     nx.draw(G, pos, with_labels=True, node_size=700, node_color='skyblue', font_size=10, font_weight='bold')  # 绘制节点
#     nx.draw_networkx_edges(G, pos, edgelist=edgelist, width=2, edge_color='gray')  # 绘制边
#     plt.show()
#
#
# # 示例节点列表和边列表
# nodelist = [1, 2, 3, 4, 5]
# edgelist = [(1, 2), (1, 3), (2, 3), (3, 4), (4, 5)]
#
# # 绘制图
# draw_graph(nodelist, edgelist)
import networkx as nx
import matplotlib.pyplot as plt
import utils
import globals
import json


def draw_graph(nodelist, edgelist):
    # 创建一个带权图对象
    G = nx.Graph()

    # 添加节点
    G.add_nodes_from(nodelist)

    # 添加带权边
    for edge in edgelist:
        G.add_edge(edge[0], edge[1], weight=float(edge[2]))

    # 绘制图
    pos = nx.kamada_kawai_layout(G)
    # pos = nx.spring_layout(G, scale=10000)  # 使用spring布局算法确定节点的位置
    labels = nx.get_edge_attributes(G, 'weight')  # 获取边的权重
    # nx.draw(G, pos, with_labels=True)  # 绘制节点
    nx.draw(G, pos, with_labels=True, node_size=700, node_color='skyblue', font_size=5, font_weight='bold')  # 绘制节点
    nx.draw_networkx_edges(G, pos, edgelist=edgelist, width=2, edge_color='gray')  # 绘制边
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)  # 绘制边的权重
    plt.show()


# 示例节点列表和带权边列表
# nodelist = [1, 2, 3, 4, 5]
# edgelist = [(1, 2, 3), (1, 3, 4), (2, 3, 5), (3, 4, 2), (4, 5, 1)]
# with open("simData/simData02/graphdata.json", 'r') as file:
with open("simData/newInitJavaData.json", 'r', encoding='utf-8') as file:
    data = json.load(file)
graphdata = data['graphData']
utils.parse_data_to_init_resources(graphdata, globals.EDGE_INFO, globals.NODE_INFO)
node_obj_list = globals.NODE_INFO.values()
nodelist = [node_obj.node_id for node_obj in node_obj_list]
edge_obj_list = globals.EDGE_INFO.values()
edgelist = [(edge_obj.start_node, edge_obj.end_node, edge_obj.length) for edge_obj in edge_obj_list]

# 绘制图
draw_graph(nodelist, edgelist)
