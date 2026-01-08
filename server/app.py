from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
import time
import threading

from server.shooting import handle_shoot, update_shots
from server.ghost import get_ghost_position, prune_history, DEFAULT_GHOST_DELAY, MIN_GHOST_DELAY, MAX_GHOST_DELAY

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game constants
BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
MOVE_AMOUNT = 3
START_X = BOX_WIDTH // 2
START_Y = BOX_HEIGHT // 2

DELAY_CHANGE_RATE = 0.0175

GAMESTATE_EMIT_INTERVAL = 1.0 / 60
SHOOT_COOLDOWN = 1.0

# Server-side game state
players = {}
shots = []

# --- Movement state for each player (server authoritative) ---
# For each player: {'move': {'up': False, 'down': False, 'left': False, 'right': False}}

def get_blank_move_state():
    return {'left': False, 'right': False, 'up': False, 'down': False}

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
        'last_shot': 0,
        'move': get_blank_move_state()
    }
    # Start background thread once
    global broadcast_thread
    if not hasattr(on_connect, "broadcast_thread"):
        on_connect.broadcast_thread = socketio.start_background_task(game_state_broadcast_loop)

# --- Movement handler: update server-side movement state ---
@socketio.on('move_start')
def handle_move_start(data):
    direction = data.get('dir')
    p = players.get(request.sid)
    if p and direction in p['move']:
        p['move'][direction] = True

@socketio.on('move_stop')
def handle_move_stop(data):
    direction = data.get('dir')
    p = players.get(request.sid)
    if p and direction in p['move']:
        p['move'][direction] = False

@socketio.on('shoot')
def on_shoot():
    p = players.get(request.sid)
    now = time.time()
    if not p:
        return
    if now - p.get('last_shot', 0) < SHOOT_COOLDOWN:
        return
    p['last_shot'] = now
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

def clamp(val, minv, maxv):
    return max(minv, min(maxv, val))

def update_player_positions():
    now = time.time()
    for p in players.values():
        dx = 0
        dy = 0
        move = p['move']
        if move.get('left'):  dx -= 1
        if move.get('right'): dx += 1
        if move.get('up'):    dy -= 1
        if move.get('down'):  dy += 1
        # Normalize diagonal
        if dx != 0 and dy != 0:
            length = (dx ** 2 + dy ** 2) ** 0.5
            dx /= length
            dy /= length
        new_x = p['x'] + dx * MOVE_AMOUNT
        new_y = p['y'] + dy * MOVE_AMOUNT
        new_x = clamp(new_x, PLAYER_RADIUS, BOX_WIDTH - PLAYER_RADIUS)
        new_y = clamp(new_y, PLAYER_RADIUS, BOX_HEIGHT - PLAYER_RADIUS)
        if new_x != p['x'] or new_y != p['y']:
            p['x'] = new_x
            p['y'] = new_y
            if 'history' not in p:
                p['history'] = []
            p['history'].append({'x': new_x, 'y': new_y, 't': now})
            max_player_delay = p.get('delay', DEFAULT_GHOST_DELAY)
            max_age = max(MAX_GHOST_DELAY, max_player_delay) + 0.5
            p['history'] = prune_history(p['history'], now, max_age)

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
    for p in players.values():
        if p.get('delay_inc'):
            p['delay'] = min(MAX_GHOST_DELAY, p.get('delay', DEFAULT_GHOST_DELAY) + DELAY_CHANGE_RATE)
        if p.get('delay_dec'):
            p['delay'] = max(MIN_GHOST_DELAY, p.get('delay', DEFAULT_GHOST_DELAY) - DELAY_CHANGE_RATE)

def game_state_broadcast_loop():
    while True:
        update_player_positions()
        process_delays()
        update_shots(players, shots)
        emit_game_state()
        socketio.sleep(GAMESTATE_EMIT_INTERVAL)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
