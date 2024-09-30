import eventlet
import socketio
from threading import Lock
import random

thread = None
thread_lock = Lock()

sio = socketio.Server()
app = socketio.WSGIApp(sio, static_files={
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
})


@sio.on('connect')
def test_connect(sid, environ):
    print('Client connected:', sid)
    # global thread
    # with thread_lock:
    #     if thread is None:
    #         thread = sio.start_background_task(target=background_thread)


@sio.on('startService')
def testSendData(sid, flag):
    # print(flag, type(flag))
    if int(flag) == 1:
        global thread
        with thread_lock:
            if thread is None:
                thread = sio.start_background_task(target=background_thread)


def background_thread():
    while True:
        sio.sleep(2)
        t = random.randint(1, 100)
        # socketio.emit('server_response', {'data': t}, namespace='/test_conn')
        sio.emit('server_response', {'data': t})


@sio.on('receive')
def handle_agv_data(sid, data):
    print("Received agv data:", data)


@sio.on('disconnect')
def test_disconnect(sid):
    print('Client disconnected: ', sid)


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
