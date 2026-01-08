from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
import time
import threading
import math

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state: mapping of session IDs to player info
players = {}

BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
MOVE_AMOUNT = 3
START_X = BOX_WIDTH // 2
START_Y = BOX_HEIGHT // 2

GHOST_DELAY = 1.0  # seconds
GAMESTATE_EMIT_INTERVAL = 1.0 / 60  # 60 FPS

SHOT_SPEED = 6
SHOT_RADIUS = 5

shots = []  # Each shot: {'x', 'y', 'vx', 'vy', 'owner', 'target_sid'}

@app.route('/')
def index():
    return send_from_directory('../client', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('../client', path)

def prune_history(history, now, max_age):
    # Remove entries older than max_age
    return [h for h in history if now - h['t'] <= max_age]

def get_ghost_position(history, now, delay):
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
        # Interpolate
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
def handle_connect():
    now = time.time()
    players[request.sid] = {
        'x': START_X,
        'y': START_Y,
        'history': [{'x': START_X, 'y': START_Y, 't': now}],
        'score': 0
    }

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
    # Keep enough history for the ghost delay plus margin
    max_age = GHOST_DELAY + 0.5
    p['history'] = prune_history(p['history'], now, max_age)

@socketio.on('shoot')
def handle_shoot():
    shooter = players.get(request.sid)
    if not shooter:
        return
    # Find the nearest enemy ghost
    now = time.time()
    target_sid = None
    target_ghost = None
    min_dist = None
    for sid, p in players.items():
        if sid == request.sid:
            continue
        ghost = get_ghost_position(p['history'], now, GHOST_DELAY)
        if ghost is None:
            continue
        dist = math.hypot(ghost['x'] - shooter['x'], ghost['y'] - shooter['y'])
        if min_dist is None or dist < min_dist:
            min_dist = dist
            target_sid = sid
            target_ghost = ghost
    if target_sid is None or target_ghost is None:
        return  # No target
    # Compute velocity vector
    dx = target_ghost['x'] - shooter['x']
    dy = target_ghost['y'] - shooter['y']
    dist = math.hypot(dx, dy)
    if dist == 0:
        return
    vx = dx / dist * SHOT_SPEED
    vy = dy / dist * SHOT_SPEED
    shots.append({
        'x': shooter['x'],
        'y': shooter['y'],
        'vx': vx,
        'vy': vy,
        'owner': request.sid,
        'target_sid': target_sid,
    })

@socketio.on('disconnect')
def handle_disconnect():
    players.pop(request.sid, None)
    # Remove shots owned by or targeting this player
    global shots
    shots = [shot for shot in shots if shot['owner'] != request.sid and shot['target_sid'] != request.sid]

def update_shots():
    global shots
    now = time.time()
    to_remove = []
    for shot in shots:
        shot['x'] += shot['vx']
        shot['y'] += shot['vy']
        # Remove if out of bounds
        if not (0 <= shot['x'] <= BOX_WIDTH and 0 <= shot['y'] <= BOX_HEIGHT):
            to_remove.append(shot)
            continue
        # Check collision with target ghost
        target_player = players.get(shot['target_sid'])
        if not target_player:
            to_remove.append(shot)
            continue
        ghost = get_ghost_position(target_player['history'], now, GHOST_DELAY)
        if ghost:
            dx = shot['x'] - ghost['x']
            dy = shot['y'] - ghost['y']
            if (dx ** 2 + dy ** 2) <= (PLAYER_RADIUS ** 2):
                # Score!
                owner = players.get(shot['owner'])
                if owner:
                    owner['score'] = owner.get('score', 0) + 1
                to_remove.append(shot)
    for shot in to_remove:
        if shot in shots:
            shots.remove(shot)

def emit_game_state():
    now = time.time()
    state = {}
    for sid, p in players.items():
        ghost_pos = get_ghost_position(p['history'], now, GHOST_DELAY)
        state[sid] = {
            'x': p['x'],
            'y': p['y'],
            'ghost': ghost_pos,
            'score': p.get('score', 0)
        }
    # Add shots to state
    state['shots'] = [
        {'x': s['x'], 'y': s['y']} for s in shots
    ]
    socketio.emit('state', state)

def game_state_broadcast_loop():
    while True:
        update_shots()
        emit_game_state()
        socketio.sleep(GAMESTATE_EMIT_INTERVAL)

@socketio.on('connect')
def start_broadcast_loop():
    # Start the broadcast thread only once, when the first client connects
    global broadcast_thread
    if not hasattr(start_broadcast_loop, "broadcast_thread"):
        start_broadcast_loop.broadcast_thread = socketio.start_background_task(game_state_broadcast_loop)
    # Register player (ensure connect logic still runs)
    now = time.time()
    players[request.sid] = {
        'x': START_X,
        'y': START_Y,
        'history': [{'x': START_X, 'y': START_Y, 't': now}],
        'score': 0
    }

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)