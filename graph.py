class Node:
    region_id = None

    def __init__(self, node_id, label):
        self.node_id = node_id
        self.wait_queue = []  # 当前已经在节点相连的边上，后续到达的AGV
        self.pass_queue = []  # 在节点2倍安全距离以内的AGV
        self.locked = False
        self.locked_by = None
        self.label = label
        self.region_id = None
        # self.associated_path = []
        # self.status = None

    def add_agv_to_wait_queue(self, agv_id):
        if agv_id not in self.wait_queue:
            self.wait_queue.append(agv_id)

    def add_agv_to_pass_queue(self, agv_id):
        if agv_id not in self.pass_queue:
            self.pass_queue.append(agv_id)

    def remove_agv_from_wait_queue(self, agv_id):
        if agv_id in self.wait_queue:
            self.wait_queue.remove(agv_id)

    def remove_agv_from_pass_queue(self, agv_id):
        if agv_id in self.pass_queue:
            self.pass_queue.remove(agv_id)

    def lock(self, agv_id):
        # if not self.locked:
        #     self.locked = True
        #     self.locked_by = agv_id
        #     print(f"AGV {agv_id} 已经锁定交叉路口。")
        # else:
        #     print(f"AGV {agv_id} 锁定交叉路口失败，AGV {self.locked_by} 已经锁定交叉路口未释放。")
        if self.locked and self.locked_by != agv_id:
            print(
                f"AGV {agv_id} 试图锁定交叉路口{self.node_id}，但AGV {self.locked_by} 已经锁定交叉路口未释放, 请检查代码！。")
        self.locked = True
        self.locked_by = agv_id
        print(f"AGV编号 {agv_id} 已经锁定节点{self.node_id}。")

    def unlock(self, agv_id):
        if self.locked and self.locked_by == agv_id:
            self.locked = False
            self.locked_by = None
            print(f"AGV {agv_id} 已经解锁交叉路口{self.node_id}。")

    @classmethod
    def getRegion(cls):
        return cls.region_id

    @classmethod
    def setRegion(cls, region_id):
        cls.region_id = region_id


class Edge:
    region_id = None

    def __init__(self, edge_id, start_node, end_node, length, width, speed, label):
        self.edge_id = edge_id
        self.start_node = start_node
        self.end_node = end_node
        self.length = length
        self.weight = None
        self.width = width
        self.speed = speed
        self.status = 0
        # 当前处于该路段的AGV列表,存储agv_id
        self.occupy_agv_id = []
        self.label = label

        self.bidirection = False  # 用于标识该条边是否为双向边
        self.locked = False  # 用于标识双向路段是否被占用
        self.locked_by = None

    def remain_capacity(self, agvs_dict, safe_vehicle_interval):
        # 单向图：剩余容量由位于该路段最后的 AGV 的位置决定，已考虑安全间隔, 大于车长即可
        # if self.occupy_agv_id:
        #     total_length = 0
        #     for agv_id in self.occupy_agv_id:
        #         total_length += glob.AGV_VEHICLES[agv_id].length + glob.SAFE_VEHICLE_INTERVAL
        #     remaining_length = self.length - total_length
        # else:
        #     remaining_length = self.length
        #
        # return remaining_length
        if self.locked:
            return 0
        else:
            if self.occupy_agv_id:
                pos_percent_list = [agvs_dict[agv_id].pos_percent for agv_id in self.occupy_agv_id]
                # min_agv_id = min(zip(self.occupy_agv_id, pos_percent_list), key=lambda x: x[1])[0]
                remain_length = min(pos_percent_list) * self.length - safe_vehicle_interval
                return remain_length
            else:
                return self.length

    def update_occupy_agv(self, agv_obj, agvs_dict, edges_dict):
        if agv_obj.current_edge_id == self.edge_id:
            # if agv_obj.status in [1, 4] and agv_obj.id not in self.occupy_agv_id:
            if self.bidirection:
                self.lock(agv_obj.id)
                reverse_edge_id = f"{self.end_node}-{self.start_node}"
                reverse_edge = edges_dict[reverse_edge_id]
                reverse_edge.lock(agv_obj.id)

            if agv_obj.id not in self.occupy_agv_id:
                self.occupy_agv_id.append(agv_obj.id)
                # 按照位置百分比从小到大排序
                self.sort_occupy_agv(agvs_dict)
            # elif agv_obj.status not in [1, 4] and agv_obj.id in self.occupy_agv_id:
            #     self.occupy_agv_id.remove(agv_obj.id)
            #     # 按照位置百分比从小到大排序
            #     self.sort_occupy_agv(agvs_dict)
        else:
            if self.bidirection:
                self.unlock(agv_obj.id)
                reverse_edge_id = f"{self.end_node}-{self.start_node}"
                reverse_edge = edges_dict[reverse_edge_id]
                reverse_edge.unlock(agv_obj.id)

            if agv_obj.id in self.occupy_agv_id:
                self.occupy_agv_id.remove(agv_obj.id)
                # 按照位置百分比从小到大排序
                self.sort_occupy_agv(agvs_dict)

    def lock(self, agv_id):
        if self.locked:
            if self.locked_by != agv_id:
                raise ValueError(f"双向边{self.edge_id}被{self.locked_by}锁定未释放，但有车辆{agv_id}试图锁定，请进一步检查！")
            else:
                print(f"双向边{self.edge_id}被{self.locked_by}锁定，该车辆正在占用该路段，不允许其他车辆进入")
        else:
            self.locked = True
            self.locked_by = agv_id
            print(f"AGV编号 {agv_id} 已经锁定双向边{self.edge_id}。")

    def unlock(self, agv_id):
        if self.locked and self.locked_by == agv_id:
            self.locked = False
            self.locked_by = None
            print(f"AGV {agv_id} 已经解锁双向边{self.edge_id}。")

    def sort_occupy_agv(self, agvs_dict):
        if self.occupy_agv_id:
            positions = [agvs_dict[agv_id].pos_percent for agv_id in self.occupy_agv_id]
            agv_tuples = zip(self.occupy_agv_id, positions)
            # 按照位置百分比排序
            sorted_agv_tuples = sorted(agv_tuples, key=lambda x: x[1])
            # 提取排序后的 agv_id
            self.occupy_agv_id = [agv_id for agv_id, _ in sorted_agv_tuples]

    def info(self):
        print("Edge编号：", self.edge_id, "线长：", self.length, "线宽：", self.width, "线速：", self.speed)

    @classmethod
    def getRegion(cls):
        return cls.region_id

    @classmethod
    def setRegion(cls, region_id):
        cls.region_id = region_id

    # def add_occupy_agv(self, agv_id):
    #     if agv_id not in self.occupy_agv_id:
    #         self.occupy_agv_id.append(agv_id)
    #
    # def remove_occupy_agv(self, agv_id):
    #     if agv_id in self.occupy_agv_id:
    #         self.occupy_agv_id.remove(agv_id)


# 检查双向边的锁定状态是否保持一致
def check_lock_status():
    pass


class Graph:
    def __init__(self, data):
        self.node = []
        self.edge = {}
        for item in data:
            # data 格式: [[节点1（node_id），节点2，路径编号(edge_id)], ...]
            # data = [['A', 'B', 'seg1'], ['A', 'D', 'seg2'], ['B', 'C', 'seg3'], ['C', 'D', 'seg4']]
            # 读取数据后建立静态图的同时，创建上面的node和edge实例监控对象
            from_node, to_node, edge_id = item
            if from_node not in self.node:
                self.node.append(from_node)
            if to_node not in self.node:
                self.node.append(to_node)
            if from_node not in self.edge:
                self.edge[from_node] = {}
            self.edge[from_node][to_node] = edge_id

    # def add_node(self, node_id):
    #     self.node.append(node_id)
    #
    # def add_edge(self, start_value, end_value):
    #     start_node = None
    #     end_node = None
    #     for node in self.nodes:
    #         if node.value == start_value:
    #             start_node = node
    #         elif node.value == end_value:
    #             end_node = node
    #     if start_node and end_node:
    #         start_node.neighbors.append(end_node)
    #         self.edges.append(Edge(start_node, end_node))


if __name__ == '__main__':
    data = [['A', 'B', 'seg1'], ['A', 'D', 'seg2'], ['B', 'C', 'seg3'], ['C', 'D', 'seg4']]
    g = Graph(data)
    print(g.node)
    print(g.edge)
    print(g.edge['A']['B'])
