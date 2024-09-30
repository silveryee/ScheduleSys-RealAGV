import numpy as np
import copy


class Order:
    def __init__(self, order_id, area_id, target_list, ):

        self.order_id = order_id
        self.area_id = area_id
        self.target_list = target_list
        # target_list格式：字典列表，"nodeTime"
        # {
        #     "nodeId": "siteB",
        #     "postionX": 190.33,
        #     "postionY": 270.20,
        #     "nodeTime": 12 // 单位：秒[>0]表示该点需要停留
        #     "nodeType": "LM",  # 取货点
        #     "container": {
        #       "length": 1.5,  # 长
        #       "width": 0.4,   # 宽
        #       "height": 1.2   # 高
        #     }
        # }

        self.assigned_agv_id = None
        self.site_list = None
        self.wait_time_list = None
        self.finished = False

    def update(self, assigned_agv_id, site_list):
        self.assigned_agv_id = assigned_agv_id
        self.site_list = copy.deepcopy(site_list)
        self.wait_time_list = generate_wait_time(self.target_list, self.site_list)

    # def target_info(self):
    #     target_node_list = [{site["nodeId"]:site["nodeTime"]} for site in self.target_list]

    def info(self):
        print("*"*50, f"订单{self.order_id}信息", "*"*50)
        # print('TargetList:', self.target_list)
        print('TargetList:', [{site["nodeId"]:site["nodeTime"]} for site in self.target_list])
        print('AssignedAGVID:', self.assigned_agv_id)
        print('SiteList:', self.site_list)
        print('WaitTimeList:', self.wait_time_list)

    def finish(self):
        self.finished = True


def generate_wait_time(targetList, siteList):
    target_list = copy.deepcopy(targetList)
    wait_time_list = [0] * len(siteList)

    for index, site_node in enumerate(siteList):
        if target_list:
            if site_node == target_list[0]['nodeId']:
                wait_time_list[index] = target_list[0]['nodeTime']
                target_list.pop(0)
            else:
                continue
    return wait_time_list

