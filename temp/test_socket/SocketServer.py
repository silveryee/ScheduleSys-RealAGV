#coding: utf-8

"""
Socket 搭建简单服务器
https://www.cnblogs.com/qsyll0916/p/8660744.html
"""

import socket

HOST = '10.9.58.60'         # 获取本地主机名,cmd下用ipconfig命令查看
PORT = 12345                # 设置端口号
ADDR = (HOST, PORT)         # 放在一起就是套接字了
web = socket.socket()       # 创建socket对象
web.bind(ADDR)              # 绑定端口

web.listen(5)               # 等待客户端连接，参数为TCP连接队列的大小,就是连接数
print('sever is listening...')

while True:
    client_connection, client_address = web.accept()  # 建立客户端连接
    print('link addr:')
    print(client_address)   # 打印客户端发来的嵌套字

    client_connection.send(str.encode("HELLO,WORLD"))   # 向客户端发送信息，需要byte类型的参数，需要做一下转换

    data = client_connection.recv(1024)
    print(data)

    client_connection.close()       #关闭连接