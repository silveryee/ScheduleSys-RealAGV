import socketio

sio = socketio.Client()

namespace = '/simScript'
# @sio.event
# def connect():
#     print('connection established')

# 连接事件处理
@sio.event(namespace=namespace)
def connect():
    print(f"Connected to namespace {namespace}")

@sio.event
def my_message(data):
    print('message received with ', data)
    sio.emit('my response', {'response': 'my response'})


@sio.event
def disconnect():
    print('disconnected from server')


if __name__ == '__main__':
    sio.connect('http://127.0.0.1:5000', wait_timeout=10)
    sio.wait()
