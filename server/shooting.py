# server/shooting.py

import math
import time
from server.ghost import get_ghost_position, DEFAULT_GHOST_DELAY

BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
SHOT_SPEED = 6
SHOT_RADIUS = 5

def handle_shoot(players, shots, shooter_sid):
    shooter = players.get(shooter_sid)
    if not shooter:
        return

    now = time.time()
    # Find the closest target's ghost
    target_sid = None
    target_ghost = None
    min_dist = None
    for sid, p in players.items():
        if sid == shooter_sid:
            continue
        delay = p.get('delay', DEFAULT_GHOST_DELAY)
        ghost = get_ghost_position(p['history'], now, delay)
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
        delay = target_player.get('delay', DEFAULT_GHOST_DELAY)
        ghost = get_ghost_position(target_player['history'], now, delay)
        if ghost:
            dx = shot['x'] - ghost['x']
            dy = shot['y'] - ghost['y']
            if (dx ** 2 + dy ** 2) <= (PLAYER_RADIUS ** 2):
                # Score for the shooter!
                owner = players.get(shot['owner'])
                if owner:
                    owner['score'] = owner.get('score', 0) + 1
                to_remove.append(shot)
    for shot in to_remove:
        if shot in shots:
            shots.remove(shot)