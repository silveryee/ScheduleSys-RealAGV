import threading
import time


class Intersection:
    def __init__(self):
        self.locked = False
        self.locked_by = None
        self.remaining_length = 5  # 假设路径端剩余长度为5

    def request_entry(self, agv_id):
        while True:
            if not self.locked:
                self.lock(agv_id)
                return True
            else:
                time.sleep(0.5)  # 每0.5秒发送一次请求
                print(f"AGV {agv_id} 正在等待解锁交叉路口...")

    def lock(self, agv_id):
        self.locked = True
        self.locked_by = agv_id
        print(f"AGV {agv_id} 已经锁定交叉路口。")

    def unlock(self, agv_id):
        if self.locked and self.locked_by == agv_id:
            self.locked = False
            self.locked_by = None
            print(f"AGV {agv_id} 已经解锁交叉路口。")

    def pass_intersection(self, agv_id):
        print(f"AGV {agv_id} 正在通过交叉路口...")
        time.sleep(5)  # 模拟通过交叉路口的时间
        print(f"AGV {agv_id} 已经通过交叉路口。")
        self.unlock(agv_id)

# 创建交叉路口对象
intersection = Intersection()

# 创建AGV线程
def agv_thread(agv_id):
    while True:
        if intersection.request_entry(agv_id):
            intersection.pass_intersection(agv_id)
            break

# 启动AGV线程
agv_threads = []
for i in range(3):
    thread = threading.Thread(target=agv_thread, args=(i,))
    agv_threads.append(thread)
    thread.start()

# 等待所有AGV线程完成
for thread in agv_threads:
    thread.join()

print("所有AGV已通过交叉路口。")
