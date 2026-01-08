# server/shooting.py

import math
import time

BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
GHOST_DELAY = 1.0
SHOT_SPEED = 6
SHOT_RADIUS = 5

def get_ghost_position(history, now, delay):
    target_time = now - delay
    if not history:
        return None
    h1, h2 = None, None
    for i in range(len(history) - 1):
        if history[i]['t'] <= target_time <= history[i + 1]['t']:
            h1 = history[i]
            h2 = history[i + 1]
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

def handle_shoot(players, shots, shooter_sid):
    shooter = players.get(shooter_sid)
    if not shooter:
        return
    now = time.time()
    target_sid = None
    target_ghost = None
    min_dist = None
    for sid, p in players.items():
        if sid == shooter_sid:
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
        return
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
        'owner': shooter_sid,
        'target_sid': target_sid,
    })

def update_shots(players, shots):
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