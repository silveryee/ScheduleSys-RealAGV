# 返回列表中第一个通过下一路段容量检查的agv_id
import agv


def select_satisfy_path_capacity_agv(agv_id_candidates, agvs_dict, edges_dict, safe_vehicle_interval):
    for agv_id in agv_id_candidates:
        agv_obj = agvs_dict[agv_id]
        target_edge_obj = edges_dict[agv_obj.next_edge_id]
        if target_edge_obj.remain_capacity(agvs_dict, safe_vehicle_interval) > agv_obj.length:
            return agv_id
        else:
            continue
    print("当前节点所有AGV的目标路段容量已满，请等待")


# 批量禁止 AGV 通行
def batch_disable_agv_passing(cmds_dict, disable_id):
    for agv_id in disable_id:
        cmds_dict[agv_id] = 0


# 对在边上运行的AGV进行冲突检测，现阶段没有意义，因为检测到了也需要在到达节点时再进行冲突解决，可以之后优化做冲突预防，提前重调路径规划
def check_node_conflicts(agvs_dict, safety_time_interval):
    conflicts = {}
    # 统计每个节点被AGV到达的时间
    node_arrival_times = {}
    for agv in agvs_dict.values():
        if agv.status in [1, 4]:  # 只有行进或者等待中的agv才可能造成冲突，AGV 空闲（0）、做任务（2）、充电（3）不得占用节点或边的空间
            if agv.end_node_id not in node_arrival_times:
                node_arrival_times[agv.end_node_id] = []
            node_arrival_times[agv.end_node_id].append((agv.id, agv.arrival_end_node_time))

    # 检查每个节点是否存在冲突
    for node, arrivals in node_arrival_times.items():
        if len(arrivals) > 1:
            # 存在多个AGV到达同一个节点
            arrivals.sort(key=lambda x: x[1])  # 按照到达时间排序
            for i in range(1, len(arrivals)):
                agv1_id, arrival_time1 = arrivals[i - 1]
                agv2_id, arrival_time2 = arrivals[i]
                time_interval = arrival_time2 - arrival_time1
                # 时间间隔小于安全时间间隔，产生冲突
                if time_interval < safety_time_interval:
                    if node not in conflicts:
                        conflicts[node] = []
                    # 暂时以两辆车的方式表示
                    conflicts[node].append((agv1_id, agv2_id))
    return conflicts


# 对在节点的agv进行冲突解决
def solve_node_conflicts(agvs_dict, nodes_dict, edges_dict, cmds_dict, safe_vehicle_interval):
    """
    解决节点冲突，解决节点的pass_queue（已经在节点附近到达的和离开的 AGV,一个节点一次仅允许一辆 AGV 通行）
    :param agvs_dict: 全局共享变量：AGV信息
    :param nodes_dict: 全局共享变量：节点状态信息
    :param edges_dict: 全局共享变量：边状态信息
    :param cmds_dict: AGV 调度指令
    :param safe_vehicle_interval: 车辆安全间隔，globals文件中定义
    :return:cmds_dict
    """
    for node_id, node_obj in nodes_dict.items():
        if node_obj.pass_queue:
            # 如果只有一辆AGV在节点，无论是到达还是离开，均让该AGV锁定节点，之后根据任务执行情况判断通行与否
            if len(node_obj.pass_queue) == 1:
                agv_id = node_obj.pass_queue[0]
                node_obj.lock(agv_id)
                # 非任务状态让该AGV通行
                if agvs_dict[agv_id].status != 2:
                    cmds_dict[agv_id] = 1
                    # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} has "
                    #       f"no task to execute at the current node and may pass through directly. ")
                    # print("Node {node_id} pass queue has only one AGV {agv_id}")
                    print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}")
                else:
                    # 任务未执行完，继续等待
                    if agvs_dict[agv_id].waitCounter:
                        cmds_dict[agv_id] = 0
                        # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} is "
                        #       f"currently executing the task at this node and has not yet completed it. ")
                        print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}, 正在执行任务")
                    # 任务执行完毕，让该AGV通行
                    else:
                        cmds_dict[agv_id] = 1
                        # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} has "
                        #       f"finished executing the task at this node and is clear to move on. ")
                        print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}, 任务执行完毕准备通行")
            else:
                # 如果有多辆AGV在节点，先解决离开的AGV(start_node是该节点)，命令剩余AGV等待
                departing_agv_ids = []
                arriving_agv_ids = []
                for agv_id in node_obj.pass_queue:
                    if agvs_dict[agv_id].start_node_id == node_id:
                        departing_agv_ids.append(agv_id)
                    elif agvs_dict[agv_id].end_node_id == node_id:
                        arriving_agv_ids.append(agv_id)
                    else:
                        # print(f"Error: {node_id} pass queue doesn't match the current position of AGV {agv_id}")
                        raise ValueError(f"Error: {node_id} pass queue doesn't "
                                         f"match the current position of AGV {agv_id}")
                # 离开状态的AGV多于1辆:异常！
                if len(departing_agv_ids) > 1:
                    raise ValueError(f"Node {node_id} has more than one AGV passing through!")
                # 离开状态的AGV 仅有1辆
                elif departing_agv_ids:
                    # 如果节点是锁定状态，检查是否被这辆正在离开的agv锁定，是(正常状态)：该agv继续通行，pass_queue中其余agv等待
                    # 否(异常)：说明出现节点被其他agv锁定未进行释放，需要进行检查！
                    if node_obj.locked:
                        if node_obj.locked_by == departing_agv_ids[0]:
                            # 非执行任务状态
                            if agvs_dict[node_obj.locked_by].status != 2:
                                print(f"There is only one AGV in the departing state at the node: {node_id},"
                                      f"AGV: {node_obj.locked_by} is passing through the node: {node_id}...")
                                cmds_dict[node_obj.locked_by] = 1
                                # 剩余所有agv等待
                                disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                       if agv_id != node_obj.locked_by]
                                batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            # 执行任务状态
                            else:
                                # 任务未执行完毕
                                if agvs_dict[node_obj.locked_by].waitCounter:
                                    print(f"There is only one AGV in the departing state at the node: {node_id}, and "
                                          f"AGV: {node_obj.locked_by} is executing the task at this node and "
                                          f"has not yet completed it, all AGVs is waiting...")
                                    # 所有agv等待
                                    disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue]
                                    batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                                # 任务执行完毕，让该AGV通行
                                else:
                                    cmds_dict[node_obj.locked_by] = 1
                                    disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                           if agv_id != node_obj.locked_by]
                                    batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                                    print(f"There is only one AGV in the departing state at the node: {node_id}, and "
                                          f"the AGV {node_obj.locked_by} has finished executing the task at this node "
                                          f"and is clear to move on, other AGVs is waiting...")

                        else:
                            print(f"Error: Node {node_id} has not been released, "
                                  f"and is occupied by AGV {node_obj.locked_by}, please check!")
                            # raise ValueError(f"Error: Node {node_id} has not been released, "
                            #       f"and is occupied by AGV {node_obj.locked_by}, please check!")
                    else:
                        # 如果节点未被锁定，但是agv的位置已经在离开状态了，说明在进入节点时未进行锁定，可能是agv初始位置就在这里，
                        # 如果不是agv初始位置就在这里，是异常状态，需要检查！(可指定AGV初始位置规则在节点的到达区非离开区)
                        node_obj.lock(departing_agv_ids[0])
                        # print(f"AGV {departing_agv_ids[0]} entering the node {node_id} "
                        #       f"without permission, please check if the AGV's initial position is at this node!")
                        print(f"AGV {departing_agv_ids[0]} 未申请资源占用节点 {node_id}，检查初始位置是否是该节点，"
                              f"若不是请检查代码！")

                        if agvs_dict[departing_agv_ids[0]].status != 2:
                            cmds_dict[departing_agv_ids[0]] = 1
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                   if agv_id != departing_agv_ids[0]]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                        else:
                            if agvs_dict[node_obj.locked_by].waitCounter:
                                # 未执行完任务，所有agv等待
                                disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue]
                                batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            else:
                                # 已执行完任务
                                cmds_dict[node_obj.locked_by] = 1
                                disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                       if agv_id != node_obj.locked_by]
                                batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                else:
                    # 没有离开状态的AGV,只有进入状态的agv
                    # ===============================test!!!!之后删除==================================
                    if not departing_agv_ids and node_obj.pass_queue == arriving_agv_ids:
                        print(f"节点{node_id} 没有正在通行离开节点的AGV，全部在进入节点状态")
                    # ===============================test结束！！！！！==================================
                    if node_obj.locked:
                        # 如果节点被锁定，说明之前已经下达过调度指令，分配给某辆AGV,该AGV还未完全通过节点,让该AGV继续通行，其余AGV等待
                        if node_obj.locked_by in arriving_agv_ids:
                            cmds_dict[node_obj.locked_by] = 1
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                   if agv_id != node_obj.locked_by]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            print(f"AGV {node_obj.locked_by} is passing through the node {node_id}...")
                        else:
                            print(f"Error: Node {node_id} has not been released, "
                                  f"and is occupied by AGV {node_obj.locked_by}, please check!")

                    else:
                        # 如果节点未被锁定，根据优先级对通行列表排序，进行下一路段容量检查，满足让其通行, 不满足说明所有agv的
                        # 目标路段容量均满，全部进行等待
                        agv_list = node_obj.pass_queue
                        # priority_list = [(agv_id, agvs_dict[agv_id].priority) for agv_id in agv_list]
                        priority_list = [agvs_dict[agv_id].priority for agv_id in agv_list]
                        sorted_pairs = sorted(zip(agv_list, priority_list), key=lambda x: x[1], reverse=True)
                        sorted_agv_list_by_priority, _ = zip(*sorted_pairs)
                        allowed_agv_id = select_satisfy_path_capacity_agv(sorted_agv_list_by_priority,
                                                                          agvs_dict, edges_dict, safe_vehicle_interval)
                        if allowed_agv_id is not None:
                            node_obj.lock(allowed_agv_id)
                            cmds_dict[allowed_agv_id] = 1
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                   if agv_id != allowed_agv_id]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            print(f"AGV {node_obj.locked_by} is ready to pass through the node {node_id}, "
                                  f"while the rest of the AGVs wait...")
                        else:
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            print(f"All AGVs at node {node_id} need to wait because the next edge has no space...")


# 某些路径是双向边的情况，待测试版本
def solve_node_conflicts_v2(agvs_dict, nodes_dict, edges_dict, cmds_dict, safe_vehicle_interval):
    """
    解决节点冲突，解决节点的pass_queue（已经在节点附近到达的和离开的 AGV,一个节点一次仅允许一辆 AGV 通行）
    :param agvs_dict: 全局共享变量：AGV信息
    :param nodes_dict: 全局共享变量：节点状态信息
    :param edges_dict: 全局共享变量：边状态信息
    :param cmds_dict: AGV 调度指令
    :param safe_vehicle_interval: 车辆安全间隔，globals文件中定义
    :return:cmds_dict
    """
    for node_id, node_obj in nodes_dict.items():
        if node_obj.pass_queue:
            if len(node_obj.pass_queue) == 1:
                agv_id = node_obj.pass_queue[0]
                agv_obj = agvs_dict[agv_id]
                # 表明是进入节点状态
                if agv_obj.end_node_id == node_id:
                    # 如果节点被锁定，检查是否被该AGV锁定，是则不必再进行路径容量检查，否则表明之前有车辆未正确释放占用节点，检查代码！
                    if node_obj.locked:
                        if node_obj.locked_by == agv_id:
                            cmds_dict[agv_id] = 1
                            print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}，节点之前已锁定，正在通行进入节点")
                        else:
                            raise ValueError(
                                f"Node {node_id} has not been released, and is occupied by AGV {node_obj.locked_by}, please check!")
                    # 如果节点未被锁定，进行下一路段容量检查，通过检查锁定节点让其通行，否则原地等待
                    else:
                        # 当前节点不是终点，需要对即将进入的下一路段进行容量检查
                        if agv_obj.next_edge_id is not None:
                            next_edge = edges_dict[agv_obj.next_edge_id]
                            if next_edge.remain_capacity(agvs_dict, safe_vehicle_interval) - agv_obj.length > 0:
                                node_obj.lock(agv_id)
                                cmds_dict[agv_id] = 1
                                print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}，通过下一路段{agv_obj.next_edge_id}容量检查，锁定节点正在通行进入节点")
                            else:
                                # 目标路段容量已满，原地等待
                                cmds_dict[agv_id] = 0
                                print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}，下一路段{agv_obj.next_edge_id}容量已满，正在节点处等待")

                        else:
                            # 当前节点就是终点，锁定节点让其通行
                            node_obj.lock(agv_id)
                            cmds_dict[agv_id] = 1
                            print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}，当前节点是该AGV终点，锁定节点正在进入该节点")

                # 离开节点状态
                elif agv_obj.start_node_id == node_id:
                    # 如果节点锁定且被该AGV锁定，正常情况说明进入节点时已经锁定了，根据任务执行情况进行判断
                    if node_obj.locked:
                        if node_obj.locked_by == agv_id:
                            # 非任务状态可以通行
                            if agvs_dict[agv_id].status != 2:
                                cmds_dict[agv_id] = 1
                                # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} has "
                                #       f"no task to execute at the current node and may pass through directly. ")
                                # print("Node {node_id} pass queue has only one AGV {agv_id}")
                                print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}，正在通行离开")
                            else:
                                # 有任务且未执行完，继续等待
                                if agvs_dict[agv_id].waitCounter:
                                    cmds_dict[agv_id] = 0
                                    # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} is "
                                    #       f"currently executing the task at this node and has not yet completed it. ")
                                    print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}, 正在执行任务")
                                # 任务执行完毕，让该AGV通行
                                else:
                                    cmds_dict[agv_id] = 1
                                    # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} has "
                                    #       f"finished executing the task at this node and is clear to move on. ")
                                    print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}, 任务执行完毕准备通行")
                        else:
                            raise ValueError(
                                f"Node {node_id} has not been released, and is occupied by AGV {node_obj.locked_by}, please check!")
                    else:
                        # 应该只有初始位置在节点会遇到此种情况！要进行当前路段容量检查(做不了，当前车辆percent为0，当前路段容量肯定为0，下发订单时注意不要在双向路段即可！)
                        print(f"Node {node_id} pass queue 仅有一辆 AGV {agv_id} 处于离开节点状态，且节点未锁定，检查是否 AGV 初始位置在这里！")
                        # 非任务状态让该AGV通行
                        if agvs_dict[agv_id].status != 2:
                            # current_edge = edges_dict[agv_obj.current_edge_id]
                            # if current_edge.remain_capacity > agv_obj.length:
                            node_obj.lock(agv_id)
                            cmds_dict[agv_id] = 1
                            # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} has "
                            #       f"no task to execute at the current node and may pass through directly. ")
                            # print("Node {node_id} pass queue has only one AGV {agv_id}")
                            print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}")
                        else:
                            # 任务未执行完，继续等待
                            if agvs_dict[agv_id].waitCounter:
                                node_obj.lock(agv_id)
                                cmds_dict[agv_id] = 0
                                # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} is "
                                #       f"currently executing the task at this node and has not yet completed it. ")
                                print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}, 正在执行任务")
                            # 任务执行完毕，让该AGV通行
                            else:
                                node_obj.lock(agv_id)
                                cmds_dict[agv_id] = 1
                                # print(f"Node {node_id} pass queue has only one AGV {agv_id}, and the AGV {agv_id} has "
                                #       f"finished executing the task at this node and is clear to move on. ")
                                print(f"Node {node_id} pass queue 仅有 1 辆 AGV {agv_id}, 任务执行完毕准备通行")

                else:
                    raise ValueError(f"Node {node_id} 不是 AGV 所在路段的开始节点或结束节点，请检查代码！")
            else:
                # 如果有多辆AGV在节点，先解决离开的AGV(start_node是该节点)，命令剩余AGV等待
                departing_agv_ids = []
                arriving_agv_ids = []
                for agv_id in node_obj.pass_queue:
                    if agvs_dict[agv_id].start_node_id == node_id:
                        departing_agv_ids.append(agv_id)
                    elif agvs_dict[agv_id].end_node_id == node_id:
                        arriving_agv_ids.append(agv_id)
                    else:
                        # print(f"Error: {node_id} pass queue doesn't match the current position of AGV {agv_id}")
                        raise ValueError(f"Error: {node_id} pass queue doesn't "
                                         f"match the current position of AGV {agv_id}")
                # 离开状态的AGV多于1辆:异常！
                if len(departing_agv_ids) > 1:
                    raise ValueError(f"Node {node_id} has more than one AGV passing through!")
                # 离开状态的AGV 仅有1辆
                elif departing_agv_ids:
                    # 如果节点是锁定状态，检查是否被这辆正在离开的agv锁定，是(正常状态)：该agv继续通行，pass_queue中其余agv等待
                    # 否(异常)：说明出现节点被其他agv锁定未进行释放，需要进行检查！
                    if node_obj.locked:
                        if node_obj.locked_by == departing_agv_ids[0]:
                            # 非执行任务状态
                            if agvs_dict[node_obj.locked_by].status != 2:
                                print(f"There is only one AGV in the departing state at the node: {node_id},"
                                      f"AGV: {node_obj.locked_by} is passing through the node: {node_id}...")
                                cmds_dict[node_obj.locked_by] = 1
                                # 剩余所有agv等待
                                disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                       if agv_id != node_obj.locked_by]
                                batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            # 执行任务状态
                            else:
                                # 任务未执行完毕
                                if agvs_dict[node_obj.locked_by].waitCounter:
                                    print(f"There is only one AGV in the departing state at the node: {node_id}, and "
                                          f"AGV: {node_obj.locked_by} is executing the task at this node and "
                                          f"has not yet completed it, all AGVs is waiting...")
                                    # 所有agv等待
                                    disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue]
                                    batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                                # 任务执行完毕，让该AGV通行
                                else:
                                    cmds_dict[node_obj.locked_by] = 1
                                    disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                           if agv_id != node_obj.locked_by]
                                    batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                                    print(f"There is only one AGV in the departing state at the node: {node_id}, and "
                                          f"the AGV {node_obj.locked_by} has finished executing the task at this node "
                                          f"and is clear to move on, other AGVs is waiting...")

                        else:
                            print(f"Error: Node {node_id} has not been released, "
                                  f"and is occupied by AGV {node_obj.locked_by}, please check!")
                            # raise ValueError(f"Error: Node {node_id} has not been released, "
                            #       f"and is occupied by AGV {node_obj.locked_by}, please check!")
                    else:
                        # 如果节点未被锁定，但是agv的位置已经在离开状态了，说明在进入节点时未进行锁定，可能是agv初始位置就在这里，
                        # 如果不是agv初始位置就在这里，是异常状态，需要检查！(可指定AGV初始位置规则在节点的到达区非离开区)
                        node_obj.lock(departing_agv_ids[0])
                        # print(f"AGV {departing_agv_ids[0]} entering the node {node_id} "
                        #       f"without permission, please check if the AGV's initial position is at this node!")
                        print(f"AGV {departing_agv_ids[0]} 未申请资源占用节点 {node_id}，检查初始位置是否是该节点，"
                              f"若不是请检查代码！")

                        if agvs_dict[departing_agv_ids[0]].status != 2:
                            cmds_dict[departing_agv_ids[0]] = 1
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                   if agv_id != departing_agv_ids[0]]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                        else:
                            if agvs_dict[node_obj.locked_by].waitCounter:
                                # 未执行完任务，所有agv等待
                                disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue]
                                batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            else:
                                # 已执行完任务
                                cmds_dict[node_obj.locked_by] = 1
                                disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                       if agv_id != node_obj.locked_by]
                                batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                else:
                    # 没有离开状态的AGV,只有进入状态的agv
                    # ===============================test!!!!之后删除==================================
                    if not departing_agv_ids and node_obj.pass_queue == arriving_agv_ids:
                        print(f"节点{node_id} 没有正在通行离开节点的AGV，全部在进入节点状态")
                    # ===============================test结束！！！！！==================================
                    if node_obj.locked:
                        # 如果节点被锁定，说明之前已经下达过调度指令，分配给某辆AGV,该AGV还未完全通过节点,让该AGV继续通行，其余AGV等待
                        if node_obj.locked_by in arriving_agv_ids:
                            cmds_dict[node_obj.locked_by] = 1
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                   if agv_id != node_obj.locked_by]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            print(f"AGV {node_obj.locked_by} is passing through the node {node_id}...")
                        else:
                            print(f"Error: Node {node_id} has not been released, "
                                  f"and is occupied by AGV {node_obj.locked_by}, please check!")

                    else:
                        # 如果节点未被锁定，根据优先级对通行列表排序，进行下一路段容量检查，满足让其通行, 不满足说明所有agv的
                        # 目标路段容量均满，全部进行等待
                        agv_list = node_obj.pass_queue
                        # priority_list = [(agv_id, agvs_dict[agv_id].priority) for agv_id in agv_list]
                        priority_list = [agvs_dict[agv_id].priority for agv_id in agv_list]
                        sorted_pairs = sorted(zip(agv_list, priority_list), key=lambda x: x[1], reverse=True)
                        sorted_agv_list_by_priority, _ = zip(*sorted_pairs)
                        allowed_agv_id = select_satisfy_path_capacity_agv(sorted_agv_list_by_priority,
                                                                          agvs_dict, edges_dict, safe_vehicle_interval)
                        if allowed_agv_id is not None:
                            node_obj.lock(allowed_agv_id)
                            cmds_dict[allowed_agv_id] = 1
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue
                                                   if agv_id != allowed_agv_id]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            print(f"AGV {node_obj.locked_by} is ready to pass through the node {node_id}, "
                                  f"while the rest of the AGVs wait...")
                        else:
                            disable_agv_id_list = [agv_id for agv_id in node_obj.pass_queue]
                            batch_disable_agv_passing(cmds_dict, disable_agv_id_list)
                            print(f"All AGVs at node {node_id} need to wait because the next edge has no space...")


# 解决追及冲突（边上）
def solve_edge_conflicts(agvs_dict, edges_dict, cmds_dict, safe_vehicle_interval):
    for edge_id, edge_obj in edges_dict.items():
        running_agvs = edge_obj.occupy_agv_id
        edge_length = edge_obj.length

        if len(running_agvs) < 2:
            continue  # 如果边上运行的AGV少于两辆，跳过检测

        for i in range(len(running_agvs) - 1):
            agv1_pos = agvs_dict[running_agvs[i]].pos_percent
            agv2_pos = agvs_dict[running_agvs[i + 1]].pos_percent
            spacing = (agv2_pos - agv1_pos) * edge_length
            if spacing < safe_vehicle_interval:
                cmds_dict[running_agvs[i]] = 0
                # agvs_dict[running_agvs[i]].control_cmd = 0
                print(
                    f"Edge {edge_id}: AGV {running_agvs[i]} and AGV {running_agvs[i + 1]} "
                    f"spacing is too small: {spacing}, AGV {running_agvs[i]} is waiting")
