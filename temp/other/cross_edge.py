import threading
import time

# 定义一个信号量，模拟某个路段的可通行车辆数
semaphore = threading.Semaphore(2)  # 假设这个路段一次只能通过两辆车

# 模拟车辆申请进入路段的过程
def enter_section(vehicle_id):
    print(f"Vehicle {vehicle_id} is requesting to enter the section...")
    semaphore.acquire()
    print(f"Vehicle {vehicle_id} is entering the section...")
    time.sleep(2)  # 模拟车辆在路段内行驶的时间
    print(f"Vehicle {vehicle_id} has left the section.")
    semaphore.release()

# 创建多个车辆线程
vehicles = ["car1", "car2", "car3", "car4", "car5"]
threads = []
for vehicle_id in vehicles:
    thread = threading.Thread(target=enter_section, args=(vehicle_id,))
    threads.append(thread)
    thread.start()

# 等待所有车辆线程结束
for thread in threads:
    thread.join()

print("All vehicles have finished.")
