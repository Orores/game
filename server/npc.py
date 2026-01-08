import socketio
import time

# Configuration
SERVER_URL = 'http://localhost:5000'
MOVE_INTERVAL = 0.01  # seconds between moves
DIRECTION_SWITCH_INTERVAL = 1.0  # seconds between direction switches

sio = socketio.Client()
direction = 1  # 1 for down, -1 for up

@sio.on('connect')
def on_connect():
    print('NPC connected to server with id:', sio.sid)

@sio.on('state')
def on_state(data):
    # Not needed for direction switching by timer, but could log position if desired
    my_id = sio.sid
    if not my_id or my_id not in data:
        return
    y = data[my_id]['y']
    print(f"NPC y position: {y}")

def npc_loop():
    global direction
    last_switch = time.time()
    while True:
        now = time.time()
        if now - last_switch >= DIRECTION_SWITCH_INTERVAL:
            direction *= -1
            last_switch = now
        sio.emit('move', {'dx': 0, 'dy': direction})
        time.sleep(MOVE_INTERVAL)

if __name__ == '__main__':
    sio.connect(SERVER_URL)
    npc_loop()
