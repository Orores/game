from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Game constants ---
BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
MOVE_AMOUNT = 3
START_X = BOX_WIDTH // 2
START_Y = BOX_HEIGHT // 2

DEFAULT_GHOST_DELAY = 0.5
MIN_GHOST_DELAY = 0.0
MAX_GHOST_DELAY = 2.0
DELAY_CHANGE_RATE = 0.0175

GAMESTATE_EMIT_INTERVAL = 1.0 / 60  # 60 FPS
SHOOT_COOLDOWN = 1.0  # seconds between shots

# --- Game state ---
players = {}  # sid: {x, y, history, score, delay, delay_inc, delay_dec, last_shot}
shots = []    # [{x, y, owner, target_sid, vx, vy}]


# --- Util ---
def prune_history(history, now, max_age):
    # Only keep positions within max_age seconds
    return [h for h in history if now - h['t'] <= max_age]

def get_ghost_position(history, now, delay):
    target_time = now - delay
    if not history:
        return None
    if history[0]['t'] > target_time:
        return {'x': history[0]['x'], 'y': history[0]['y']}
    for i in range(len(history) - 1, 0, -1):
        h1 = history[i]
        h0 = history[i - 1]
        if h0['t'] <= target_time <= h1['t']:
            t = (target_time - h0['t']) / (h1['t'] - h0['t']) if h1['t'] > h0['t'] else 0
            x = h0['x'] + (h1['x'] - h0['x']) * t
            y = h0['y'] + (h1['y'] - h0['y']) * t
            return {'x': x, 'y': y}
    return {'x': history[-1]['x'], 'y': history[-1]['y']}

def handle_shoot(players, shots, sid):
    shooter = players.get(sid)
    if not shooter:
        return
    now = time.time()
    ghost_pos = get_ghost_position(shooter['history'], now, shooter.get('delay', DEFAULT_GHOST_DELAY))
    if not ghost_pos:
        return
    # Shoot at the nearest player's ghost (not self)
    target_sid = None
    min_dist = float('inf')
    for other_sid, p in players.items():
        if other_sid == sid:
            continue
        other_ghost = get_ghost_position(p['history'], now, p.get('delay', DEFAULT_GHOST_DELAY))
        if not other_ghost:
            continue
        dx = other_ghost['x'] - ghost_pos['x']
        dy = other_ghost['y'] - ghost_pos['y']
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            target_sid = other_sid
            target_pos = other_ghost
    if target_sid is None:
        return
    # Create shot moving toward target position
    dx = target_pos['x'] - ghost_pos['x']
    dy = target_pos['y'] - ghost_pos['y']
    dist = (dx ** 2 + dy ** 2) ** 0.5
    if dist == 0:
        vx, vy = 0, 0
    else:
        vx = dx / dist * 10
        vy = dy / dist * 10
    shots.append({
        'x': ghost_pos['x'],
        'y': ghost_pos['y'],
        'owner': sid,
        'target_sid': target_sid,
        'vx': vx,
        'vy': vy,
        't': now,
    })

def update_shots(players, shots):
    remove = []
    for shot in shots:
        shot['x'] += shot['vx']
        shot['y'] += shot['vy']
        # Remove if out of bounds
        if not (0 <= shot['x'] <= BOX_WIDTH and 0 <= shot['y'] <= BOX_HEIGHT):
            remove.append(shot)
            continue
        # Check collision with target ghost
        target = players.get(shot['target_sid'])
        if not target:
            remove.append(shot)
            continue
        ghost = get_ghost_position(target['history'], time.time(), target.get('delay', DEFAULT_GHOST_DELAY))
        if not ghost:
            continue
        dx = ghost['x'] - shot['x']
        dy = ghost['y'] - shot['y']
        if (dx ** 2 + dy ** 2) ** 0.5 < PLAYER_RADIUS:
            # Hit!
            players[shot['owner']]['score'] = players[shot['owner']].get('score', 0) + 1
            remove.append(shot)
    for shot in remove:
        if shot in shots:
            shots.remove(shot)

# --- Flask routes ---
@app.route('/')
def index():
    return send_from_directory('../client', 'index.html')
@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('../client', path)

# --- Socket events ---
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
    }
    # Start background thread once
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
    x = max(PLAYER_RADIUS, min(BOX_WIDTH - PLAYER_RADIUS, x))
    y = max(PLAYER_RADIUS, min(BOX_HEIGHT - PLAYER_RADIUS, y))
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
    p = players.get(request.sid)
    now = time.time()
    if not p:
        return
    if now - p.get('last_shot', 0) < SHOOT_COOLDOWN:
        return
    p['last_shot'] = now
    handle_shoot(players, shots, request.sid)

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

# --- Game state broadcast ---
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
        process_delays()
        update_shots(players, shots)
        emit_game_state()
        socketio.sleep(GAMESTATE_EMIT_INTERVAL)

# --- Main ---
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)