import eventlet
import socketio


sio = socketio.Server(async_mode='gevent')
app = socketio.WSGIApp(sio)


# @sio.event
# def connect(sid, environ):
#     print('connect ', sid)

@sio.on('connect', namespace='/simScript')
def connect(sid, environ):
    print('Simulation Script Client connected:', sid)

@sio.on('receive')
def on_message(sid, data):
    print("Received data:", data)


@sio.event
def my_message(sid, data):
    print('message ', data)


@sio.event
def disconnect(sid):
    print('disconnect ', sid)


if __name__ == '__main__':
    from gevent.pywsgi import WSGIServer

    # 使用 gevent 作为 Socket.IO 的后端
    http_server = WSGIServer(('localhost', 5000), app)
    http_server.serve_forever()