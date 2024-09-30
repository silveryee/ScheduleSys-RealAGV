import socketio

# Create two Socket.IO client instances
namespace = '/update'
sioPlatform = socketio.Client()
sioScheduling = socketio.Client()


# Handlers for sioPlatform
@sioPlatform.event
def connect_platform():
    print('sio to platform connection established')


@sioPlatform.on("resource_update")
def resource_update_platform(data):
    print('message received with', data)
    sioScheduling.emit('resource_update', data, namespace=namespace)


@sioPlatform.on("agv_data_update")
def resource_update_platform(data):
    print('message received with', data)
    sioScheduling.emit('resource_update', data, namespace=namespace)


@sioPlatform.on("order_update")
def order_update_platform(data):
    print('message received with', data)
    sioScheduling.emit('order_update', data, namespace=namespace)


@sioPlatform.event
def disconnect_platform():
    print('disconnected from platform server')


# Handlers for sioScheduling
@sioScheduling.event(namespace=namespace)
def connect_scheduling():
    print('sio to Scheduling connection established')


@sioScheduling.on("scheduled_order", namespace=namespace)
def scheduled_order_scheduling(data):
    print('message received with', data)
    sioPlatform.emit('scheduled_order', data)


@sioScheduling.event
def disconnect_scheduling():
    print('disconnected from Scheduling server')


if __name__ == '__main__':
    try:
        # sioPlatform.connect('ws://10.9.58.137:27012?userId=122', transports=['websocket'])
        sioPlatform.connect('ws://localhost:27012?userId=122', transports=['websocket'])
        # sioScheduling.connect('http://10.9.58.239:5000/update', transports=['websocket'])
        sioScheduling.connect('http://192.168.2.107:5000/update', transports=['websocket'])
        sioPlatform.wait()
        sioScheduling.wait()
    except (socketio.exceptions.ConnectionError, InterruptedError) as e:
        print(f"ConnectionError: {e}")
        sioScheduling.disconnect()
        sioPlatform.disconnect()
