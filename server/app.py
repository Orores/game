from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
import time
import threading
import math

from server.shooting import handle_shoot, update_shots  # Import shooting logic

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

# GHOST DELAY SUPPORT
DEFAULT_GHOST_DELAY = 0.5  # seconds (initial delay per player)
MIN_GHOST_DELAY = 0.1      # minimum value in seconds
MAX_GHOST_DELAY = 1.0      # maximum value in seconds
DELAY_CHANGE_RATE = 0.1    # how much to change per J/L press

GAMESTATE_EMIT_INTERVAL = 1.0 / 60  # 60 FPS

@app.route('/')
def index():
    return send_from_directory('../client', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('../client', path)

def prune_history(history, now, max_age):
    return [h for h in history if now - h['t'] <= max_age]

def get_ghost_position(history, now, delay):
    # Same logic as in shooting.py, but duplicated here for convenience
    target_time = now - delay
    if not history:
        return None
    h1, h2 = None, None
    for i in range(len(history) - 1):
        if history[i]['t'] <= target_time <= history[i+1]['t']:
            h1 = history[i]
            h2 = history[i+1]
            break
    if h1 and h2:
        t1, t2 = h1['t'], h2['t']
        ratio = (target_time - t1) / (t2 - t1) if t2 != t1 else 0
        x = h1['x'] + (h2['x'] - h1['x']) * ratio
        y = h1['y'] + (h2['y'] - h1['y']) * ratio
        return {'x': x, 'y': y}
    elif target_time <= history[0]['t']:
        return {'x': history[0]['x'], 'y': history[0]['y']}
    else:
        return {'x': history[-1]['x'], 'y': history[-1]['y']}

@socketio.on('connect')
def on_connect():
    now = time.time()
    players[request.sid] = {
        'x': START_X,
        'y': START_Y,
        'history': [{'x': START_X, 'y': START_Y, 't': now}],
        'score': 0,
        'delay': DEFAULT_GHOST_DELAY, # each player starts with their own delay
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
    # Prune only necessary history (max delay + margin)
    max_player_delay = p.get('delay', DEFAULT_GHOST_DELAY)
    max_age = max(MAX_GHOST_DELAY, max_player_delay) + 0.5
    p['history'] = prune_history(p['history'], now, max_age)

@socketio.on('shoot')
def on_shoot():
    # Call shooting mechanic from shooting.py
    handle_shoot(players, shots, request.sid)

@socketio.on('increase_delay')
def handle_increase_delay():
    p = players.get(request.sid)
    if not p:
        return
    current = p.get('delay', DEFAULT_GHOST_DELAY)
    new_delay = min(MAX_GHOST_DELAY, current + DELAY_CHANGE_RATE)
    p['delay'] = new_delay

@socketio.on('decrease_delay')
def handle_decrease_delay():
    p = players.get(request.sid)
    if not p:
        return
    current = p.get('delay', DEFAULT_GHOST_DELAY)
    new_delay = max(MIN_GHOST_DELAY, current - DELAY_CHANGE_RATE)
    p['delay'] = new_delay

@socketio.on('disconnect')
def on_disconnect():
    players.pop(request.sid, None)
    global shots
    shots = [shot for shot in shots if shot['owner'] != request.sid and shot['target_sid'] != request.sid]

def emit_game_state():
    now = time.time()
    state = {}
    for sid, p in players.items():
        # Use each player's own delay for their ghost display
        ghost_pos = get_ghost_position(p['history'], now, p.get('delay', DEFAULT_GHOST_DELAY))
        state[sid] = {
            'x': p['x'],
            'y': p['y'],
            'ghost': ghost_pos,
            'score': p.get('score', 0),
            'delay': p.get('delay', DEFAULT_GHOST_DELAY), # expose delay to client
        }
    # Add shots to state for broadcasting
    state['shots'] = [
        {'x': s['x'], 'y': s['y']} for s in shots
    ]
    socketio.emit('state', state)

def game_state_broadcast_loop():
    while True:
        update_shots(players, shots)
        emit_game_state()
        socketio.sleep(GAMESTATE_EMIT_INTERVAL)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)