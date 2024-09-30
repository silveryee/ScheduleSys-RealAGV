import math


class AGV:
    number = 0
    region_id = None

    @staticmethod
    def get_agv_state():
        pass

    def __init__(self, vehicle_id, length, width, height, agv_type=0, status=0, speed=0, battery=100, priority=0):
        # 静态属性（数据库）
        self.__vehicle_id = vehicle_id  # 唯一车辆编号
        self.__length = length  # 长
        self.__width = width  # 宽
        self.__height = height  # 高
        self.__agv_type = agv_type  # 车辆类型（待确定）
        self.priority = priority  # 车辆优先级（从低到高：0-5）

        # 动态属性（socket）

        # 位置信息
        # 仿真不启用实际坐标
        # self.pos_x = None               # 当前位置坐标 x
        # self.pos_y = None               # 当前位置坐标 y
        # self.pos_theta = None           # 当前位置朝向

        self.pos_percent = None  # 当前位置百分比
        self.current_edge_id = None  # 当前位置所在边
        self.start_node_id = None  # 当前位置所在边的起始节点
        self.end_node_id = None  # 当前位置所在边的终点
        self.start_node_dist = None  # 当前位置距离起点的距离
        self.end_node_dist = None  # 当前位置距离终点的距离
        self.arrival_end_node_time = None  # 当前位置到达终点所需时间

        # 状态信息
        self.status = status  # AGV 状态：0：空闲，1：行进，2：任务，3:充电，4：等待
        self.speed = speed  # AGV 运行时的速度
        self.last_node_id = None  # 上一个经过的节点
        self.last_edge_id = None  # 上一条经过的边
        self.next_node_id = None  # 下一个经过的节点（注意与end_node_id区分）
        self.next_edge_id = None  # 下一条经过的边
        self.waitTime = None      # 在任务节点的等待时间
        self.waitCounter = None   # 在任务节点的等待次数（等待时间/仿真脚本更新频率间隔）

        # 任务信息
        self.order_id = None  # AGV 执行任务编号
        self.target_list = None  # 任务详情（包括任务起始点、必经点、终点）
        self.site_list = None  # 路径规划结果（全局）
        self.wait_time_list = None

        # 电量信息
        self.battery = battery  # AGV 当前电量

        # 保存交通管制调度指令结果
        # 目前采用全局变量保存所有AGV的调度指令
        # self.control_cmd = 1  # 1:通行，0:等待

        # 时间窗信息
        self.start_time = None
        self.end_time = None

        AGV.number = AGV.number + 1

    @classmethod
    def total(cls):
        print("Total number of AGVs: {0}".format(cls.number))

    @property
    def id(self):
        return self.__vehicle_id

    @property
    def length(self):
        return self.__length

    @property
    def width(self):
        return self.__width

    @property
    def height(self):
        return self.__height

    @property
    def type(self):
        return self.__agv_type

    @classmethod
    def getRegion(cls):
        return cls.region_id

    @classmethod
    def setRegion(cls, region_id):
        cls.region_id = region_id

    @property
    def pos(self):
        if self.pos_percent == 0:
            return self.start_node_id
        elif self.pos_percent == 1:
            return self.end_node_id
        else:
            raise ValueError("AGV 当前位置不在节点")

    def info(self):
        print(f'AGV 编号 {self.__vehicle_id}：当前状态：{self.status}，初始位置：{self.pos}')
        # print('Length:', self.__length)
        # print('Width:', self.__width)
        # print('Height:', self.__height)
        # print('Type:', self.__agv_type)
        # print('Status:', self.status)
        # print('InitPos:', self.start_node_id)

    def dynamic_info(self):
        print('AGV {} 当前任务执行情况：'.format(self.__vehicle_id))
        print('订单编号:', self.order_id)
        print('目标节点:', self.target_list)
        print('规划路径:', self.site_list)
        print('任务等待时间列表:', self.wait_time_list)

        print('当前位置信息:')
        print('当前边ID :', self.current_edge_id)
        print('当前开始节点:', self.start_node_id)
        print('当前终止节点:', self.end_node_id)
        print('当前位置百分比:', self.pos_percent)

        print('当前状态信息:')
        print('status :', self.status)
        print('last node::', self.last_node_id)
        print('last edge:', self.last_edge_id)
        print('next node:', self.next_node_id)
        print('next edge:', self.next_edge_id)
        print('waitTime:', self.waitTime)
        print('waitCounter:', self.waitCounter)

    # 更新 agv 实时位置(基于坐标，仿真不启用)
    # def update_pos(self, position_x, position_y, position_theta):
    #     self.pos_x = position_x
    #     self.pos_y = position_y
    #     self.pos_theta = position_theta

    # 更新 agv 实时位置（基于百分比，仿真使用）
    # def init_pos_in_node(self, node_id):
    #     self.current_edge_id = None
    #     self.start_node_id = node_id
    #     self.end_node_id = None
    #     self.pos_percent = 0
    #
    # def update_pos_in_edge(self, posData):
    #     self.pos_percent = posData["posPercent"]
    #     self.current_edge_id = posData["edgeId"]
    #     self.start_node_id = posData["startNode"]
    #     self.end_node_id = posData["endNode"]
    # 静态初始位置，如果在节点：除了start_node_id 均为None
    def init_pos(self, posData):
        self.pos_percent = posData['posPercent']  # 当前位置百分比
        self.current_edge_id = posData['edgeId']  # 当前位置所在边
        self.start_node_id = posData['startNode']  # 当前位置所在边的起始节点
        self.end_node_id = posData['endNode']  # 当前位置所在边的终点

    # 动态更新时的实时位置信息
    def update_pos_info(self, posData, edges_dict, safe_vehicle_interval):
        # if self.status == 0:
        #     self.init_pos_in_node(posData["startNode"])
        # elif self.status == 1:
        #     self.update_pos_in_edge(posData)
        if self.current_edge_id is not None and self.current_edge_id != posData["edgeId"]:
            self.handle_edge_switch()

        self.current_edge_id = posData["edgeId"]
        self.start_node_id = posData["startNode"]
        self.end_node_id = posData["endNode"]
        self.pos_percent = posData["posPercent"]

        if self.current_edge_id is not None:
            self.start_node_dist, self.end_node_dist = self.cal_dist_in_edge(edges_dict)
            self.arrival_end_node_time = self.cal_arrival_time(edges_dict, safe_vehicle_interval)
        else:
            self.start_node_dist = None
            self.end_node_dist = None
            self.arrival_end_node_time = None

    def handle_edge_switch(self,):
        self.last_edge_id = self.current_edge_id
        self.last_node_id = self.start_node_id
        # try:
        #     if self.end_node_id == self.site_list[0]:
        #         self.site_list.pop(0)
        # except IndexError:
        #     pass
    #
    # def handle_task(self, time_interval):
    #     # self.waitCounter = math.ceil(self.waitTime / globals.UPDATE_TIME_INTERVAL)
    #     if self.status == 2:
    #         self.waitCounter = math.ceil(self.waitTime / time_interval)
    #         self.waitCounter -= 1

    def update_status_info(self, statusDate):
        self.status = statusDate["status"]
        self.speed = statusDate["speed"]
        # self.last_node_id = statusDate["lastNode"]
        # self.last_edge_id = statusDate["lastEdge"]
        self.next_node_id = statusDate["nextNode"]
        self.next_edge_id = statusDate["nextEdge"]
        # self.waitTime = statusDate["waitTime"]  # 在任务节点的等待时间
        # self.waitCounter = statusDate["waitCounter"]

    def update_order_info(self, orderDate, orders_dict):
        if self.order_id != orderDate["orderID"]:
            self.order_id = orderDate["orderID"]
            order_obj = orders_dict["orderID"]
            self.target_list = order_obj.target_list.copy()
            self.site_list = order_obj.site_list.copy()
            self.wait_time_list = order_obj.wait_time_list.copy()
        else:
            pass
            # if not self.site_list and self.waitCounter == 0:
            #     order_obj = orders_dict[self.order_id]
            #     if not order_obj.finished:
            #         order_obj.finish()

    def update_battery_info(self, batteryDate):
        self.battery = batteryDate["batteryLevel"]

    # 计算 AGV 到达当前边终点的时间
    def cal_arrival_time(self, edges_dict, safe_vehicle_interval):
        if self.status in [1, 4]:
            path_length = edges_dict[self.current_edge_id].length
            actual_dist = path_length * (1 - self.pos_percent)
            # 距离节点2倍安全距离算作已经到达节点
            arrival_time = 0 if actual_dist - 2 * safe_vehicle_interval < 0 else \
                (actual_dist - 2 * safe_vehicle_interval) / self.speed
        # elif self.status == 4:
        #     arrival_time = 0
        else:
            arrival_time = math.inf
        return arrival_time

    def cal_dist_in_edge(self, edges_dict):
        edge_id = self.current_edge_id
        # edge_length = edges_dict[edge_id].length
        try:
            edge_length = edges_dict[edge_id].length
        except KeyError:
            self.dynamic_info()

        passed_length = edge_length * self.pos_percent
        remaining_length = edge_length * (1 - self.pos_percent)
        # result = {
        #     self.start_node_id: passed_length,
        #     self.end_node_id: remaining_length
        # }
        # return result
        return passed_length, remaining_length

    def modify_priority(self, score):
        self.priority = score

    # 车辆载货容量，仿真不启用
    def update_capacity(self, ):
        pass

    # 未来优化：优先级模型
    def priority_score(self, ):
        return self.priority

    # 根据agv实际坐标，返回agv所在edge_id, 起点和终点的node_id，仿真不启用
    def agv_current_edge_id(self):
        pass
