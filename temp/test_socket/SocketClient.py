"""
Socket 搭建简易客户端
https://www.cnblogs.com/qsyll0916/p/8660744.html
"""

import socket

HOST = '10.9.58.60'     # 获取本地主机名
PORT = 12345                # 设置端口号
ADDR = (HOST, PORT)

web = socket.socket()

web.connect(ADDR)           # 请求与服务器建立连接
web.send(str.encode("this is client..."))   # 向服务器发送信息

data = web.recv(1024)       # 接收数据
print(data)                 # 打印出接受到的数据

web.close()