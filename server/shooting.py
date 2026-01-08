# server/shooting.py

import math
import time
from server.ghost import get_ghost_position, DEFAULT_GHOST_DELAY

BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
SHOT_SPEED = 6
SHOT_RADIUS = 5

def handle_shoot(players, shots, shooter_sid, data):
    shooter = players.get(shooter_sid)
    if not shooter or not data:
        return

    # Mouse targeting: data should have 'x' and 'y' (target position)
    target_x = data.get('x')
    target_y = data.get('y')
    if target_x is None or target_y is None:
        return

    now = time.time()

    # Use the shooter's ghost position as the origin of the shot
    shooter_delay = shooter.get('delay', DEFAULT_GHOST_DELAY)
    ghost = get_ghost_position(shooter['history'], now, shooter_delay)
    if ghost is None:
        return
    origin_x = ghost['x']
    origin_y = ghost['y']

    # Calculate direction vector from ghost to mouse position
    dx = target_x - origin_x
    dy = target_y - origin_y
    dist = math.hypot(dx, dy)
    if dist == 0:
        return
    vx = dx / dist * SHOT_SPEED
    vy = dy / dist * SHOT_SPEED

    # For collision tracking, choose the closest non-self player (ghost) at shot time
    target_sid = None
    target_ghost = None
    min_dist = None
    for sid, p in players.items():
        if sid == shooter_sid:
            continue
        delay = p.get('delay', DEFAULT_GHOST_DELAY)
        ghost_target = get_ghost_position(p['history'], now, delay)
        if ghost_target is None:
            continue
        ghost_dist = math.hypot(ghost_target['x'] - origin_x, ghost_target['y'] - origin_y)
        if min_dist is None or ghost_dist < min_dist:
            min_dist = ghost_dist
            target_sid = sid
            target_ghost = ghost_target
    if target_sid is None:
        target_sid = None  # No target, but we still fire the shot

    shots.append({
        'x': origin_x,
        'y': origin_y,
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
        # Check collision with target ghost (if any)
        target_sid = shot.get('target_sid')
        if not target_sid:
            continue
        target_player = players.get(target_sid)
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