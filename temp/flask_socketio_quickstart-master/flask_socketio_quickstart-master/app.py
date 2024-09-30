import time
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

service_state = 0
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start_service")
def start_service():
    global service_state
    service_state = 0
    while service_state == 0:
        time_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time.time())))
        print(">>>>>>", time_text)
        json_data = {"no": 1, "time": time_text, "msg": "......"}
        socketio.emit("service_msg", json_data)
        socketio.sleep(2)
    return jsonify({"start": True})


@app.route("/stop_service")
def stop_service():
    global service_state
    service_state = 9
    return jsonify({"stop": True})


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5200, debug=True, log_output=True)