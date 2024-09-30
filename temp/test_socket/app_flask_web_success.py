#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Lock
import random

async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins='*')
thread = None
thread_lock = Lock()


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


# @socketio.on('connect', namespace='/test_conn')
@socketio.on('connect')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)


def background_thread():
    while True:
        socketio.sleep(2)
        t = random.randint(1, 100)
        # socketio.emit('server_response', {'data': t}, namespace='/test_conn')
        socketio.emit('server_response', {'data': t})


# @socketio.on('disconnect', namespace='/chat')
@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    socketio.run(app, debug=True)
