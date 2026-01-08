from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
import time

from server.shooting import handle_shoot, update_shots  # Import shooting logic
from server.ghost import get_ghost_position, prune_history, DEFAULT_GHOST_DELAY, MIN_GHOST_DELAY, MAX_GHOST_DELAY

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state: mapping of session IDs to player info
players = {}
shots = []

BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
MOVE_AMOUNT = 3
START_X = BOX_WIDTH // 2
START_Y = BOX_HEIGHT // 2

DELAY_CHANGE_RATE = 0.0175  # how much to change per event

GAMESTATE_EMIT_INTERVAL = 1.0 / 60  # 60 FPS

@app.route('/')
def index():
    return send_from_directory('../client', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('../client', path)

@socketio.on('connect')
def on_connect():
    now = time.time()
    players[request.sid] = {
        'x': START_X,
        'y': START_Y,
        'history': [{'x': START_X, 'y': START_Y, 't': now}],
        'score': 0,
        'delay': DEFAULT_GHOST_DELAY,
        'delay_inc': False,
        'delay_dec': False,
    }
    # Start background thread once
    global broadcast_thread
    if not hasattr(on_connect, "broadcast_thread"):
        on_connect.broadcast_thread = socketio.start_background_task(game_state_broadcast_loop)

@socketio.on('move')
def handle_move(data):
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    now = time.time()
    p = players.get(request.sid)
    if not p:
        return
    x = p['x'] + dx * MOVE_AMOUNT
    y = p['y'] + dy * MOVE_AMOUNT
    # Clamp to boundaries
    x = max(PLAYER_RADIUS, min(BOX_WIDTH - PLAYER_RADIUS, x))
    y = max(PLAYER_RADIUS, min(BOX_HEIGHT - PLAYER_RADIUS, y))
    # Update player state and history
    p['x'] = x
    p['y'] = y
    if 'history' not in p:
        p['history'] = []
    p['history'].append({'x': x, 'y': y, 't': now})
    max_player_delay = p.get('delay', DEFAULT_GHOST_DELAY)
    max_age = max(MAX_GHOST_DELAY, max_player_delay) + 0.5
    p['history'] = prune_history(p['history'], now, max_age)

@socketio.on('shoot')
def on_shoot():
    handle_shoot(players, shots, request.sid)

# --- Continuous delay change support ---

@socketio.on('delay_inc_start')
def handle_delay_inc_start():
    p = players.get(request.sid)
    if p:
        p['delay_inc'] = True

@socketio.on('delay_inc_stop')
def handle_delay_inc_stop():
    p = players.get(request.sid)
    if p:
        p['delay_inc'] = False

@socketio.on('delay_dec_start')
def handle_delay_dec_start():
    p = players.get(request.sid)
    if p:
        p['delay_dec'] = True

@socketio.on('delay_dec_stop')
def handle_delay_dec_stop():
    p = players.get(request.sid)
    if p:
        p['delay_dec'] = False

@socketio.on('disconnect')
def on_disconnect():
    players.pop(request.sid, None)
    global shots
    shots = [shot for shot in shots if shot['owner'] != request.sid and shot['target_sid'] != request.sid]

def emit_game_state():
    now = time.time()
    state = {}
    for sid, p in players.items():
        ghost_pos = get_ghost_position(p['history'], now, p.get('delay', DEFAULT_GHOST_DELAY))
        state[sid] = {
            'x': p['x'],
            'y': p['y'],
            'ghost': ghost_pos,
            'score': p.get('score', 0),
            'delay': p.get('delay', DEFAULT_GHOST_DELAY),
        }
    state['shots'] = [
        {'x': s['x'], 'y': s['y']} for s in shots
    ]
    socketio.emit('state', state)

def process_delays():
    # Called every frame in game_state_broadcast_loop
    for p in players.values():
        # Increment delay
        if p.get('delay_inc'):
            p['delay'] = min(MAX_GHOST_DELAY, p.get('delay', DEFAULT_GHOST_DELAY) + DELAY_CHANGE_RATE)
        # Decrement delay
        if p.get('delay_dec'):
            p['delay'] = max(MIN_GHOST_DELAY, p.get('delay', DEFAULT_GHOST_DELAY) - DELAY_CHANGE_RATE)

def game_state_broadcast_loop():
    while True:
        process_delays()
        update_shots(players, shots)
        emit_game_state()
        socketio.sleep(GAMESTATE_EMIT_INTERVAL)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
