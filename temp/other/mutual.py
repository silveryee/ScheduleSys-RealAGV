# import json
# from agv import Agv
# import logging
# global AGV_DICT
#
#
# # 一开始读取数据库构建静态AGV_DICT,这里只更新AGV动态属性
#
#
# def segmeng_request_entry():
#
#
#
# def checkNeedControl(currentLankMark):
#     pass
#
#
#
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     logger = logging.getLogger(__name__)
#     update_agv_dynamic_info('agvDynamicData.json')
#     # for agv_item in agv_list:
#
# # 管控点是否需要管控
# if not checkNeedControl(currentLankMark):
#     logger.info("[AGV-NO-NEED-CONTROL]:Landmarks:{0},AGV:{1}".format(currentLankMark, agv.Id))
#     return
#
# # 查找当前管控点是否存在
# controlPoint = next((point for point in controlPointList if point.LandMarkId == currentLankMark), None)
# if controlPoint is None:
#     return
#
# # 判断是否为出口
# if controlPoint.IsExported:
#     # 将小车移除管制区
#     AgvControlGroupModelList = [m for m in AgvControlGroupModelList if not (m.Agv.Id == agv.Id and m.ControlPoint.ControlGroupId == controlPoint.ControlGroupId)]
#
#     # 遍历管制区是否有被该车管制住等待的小车，放行等待的车
#     currentControlGroupAgv = next((m for m in sorted(AgvControlGroupModelList, key=lambda x: x.EnterTime)
#                                    if m.ControlAgv == agv.Id and m.ControlPoint.ControlGroupId == controlPoint.ControlGroupId), None)
#     if currentControlGroupAgv is not None:
#         startAgv(currentControlGroupAgv.Agv)
#         AgvControlGroupModelList.remove(currentControlGroupAgv)
#         currentControlGroupAgv.ControlState = ControlState.Entering
#         AgvControlGroupModelList.append(currentControlGroupAgv)
#     return
