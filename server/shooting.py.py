import math
import time

SHOT_SPEED = 8  # pixels per frame/tick
SHOT_RADIUS = 5
SHOT_LIFETIME = 2.0  # seconds

def distance(a, b):
    return math.hypot(a['x'] - b['x'], a['y'] - b['y'])

def handle_shoot(players, shots, sid, data):
    """
    Instead of spawning a shot instantly,
    record a 'shoot' event in the player's history (with the mouse target).
    The actual shot will be spawned from history after the player's delay.
    """
    p = players.get(sid)
    if not p:
        return
    now = time.time()
    mx = data.get('x')
    my = data.get('y')
    if mx is None or my is None:
        return

    # Record a new history entry if necessary
    # If last history entry is this tick, append to it; else, make new
    append_to_last = (
        p['history']
        and abs(p['history'][-1]['t'] - now) < 0.05
    )
    if append_to_last:
        if 'actions' not in p['history'][-1]:
            p['history'][-1]['actions'] = []
        p['history'][-1]['actions'].append({
            'type': 'shoot',
            'target': (mx, my),
            'processed': False,
        })
    else:
        p['history'].append({
            'x': p['x'],
            'y': p['y'],
            't': now,
            'actions': [{
                'type': 'shoot',
                'target': (mx, my),
                'processed': False,
            }]
        })

def update_shots(players, shots):
    """
    1. Walk through each player's history up to their ghost time,
       and for each unprocessed 'shoot' action, spawn a shot.
    2. Move existing shots, remove those that expire.
    3. Check for collisions (against ghost positions at the appropriate delay).
    """
    now = time.time()

    # 1. Process historical shoot actions for each player (by their own delay)
    for sid, p in players.items():
        delay = p.get('delay', 0.4)
        ghost_time = now - delay

        for h in p.get('history', []):
            if h['t'] > ghost_time:
                break
            for action in h.get('actions', []):
                if not action.get('processed', False) and action.get('type') == 'shoot':
                    mx, my = action['target']
                    # Spawn shot from this history entry's position, aimed at (mx, my)
                    spawn_shot(shots, sid, h['x'], h['y'], mx, my, h['t'] + delay)
                    action['processed'] = True

    # 2. Advance shots
    to_remove = []
    for i, s in enumerate(shots):
        dt = now - s['spawn_time']
        if dt < 0:
            continue  # Not yet spawned (shouldn't happen, but safe)
        if dt > SHOT_LIFETIME:
            to_remove.append(i)
            continue
        s['x'] = s['origin_x'] + s['vx'] * dt
        s['y'] = s['origin_y'] + s['vy'] * dt

    # Remove expired shots
    for i in reversed(to_remove):
        del shots[i]

    # 3. Collision: shots vs. player ghosts at their own delay
    for s in list(shots):
        for sid, p in players.items():
            # Don't hit owner
            if sid == s['owner']:
                continue
            target_delay = p.get('delay', 0.4)
            ghost_time = now - target_delay
            ghost_pos = interpolate_history(p.get('history', []), ghost_time)
            if ghost_pos and distance({'x': s['x'], 'y': s['y']}, ghost_pos) < SHOT_RADIUS + 20:
                # Example: decrease score on hit
                p['score'] = p.get('score', 0) - 1
                if s in shots:
                    shots.remove(s)
                break

def spawn_shot(shots, owner_sid, x, y, tx, ty, spawn_time=None):
    """
    Add a shot to the world, launched at (x, y) toward (tx, ty).
    Store original firing time for correct movement.
    """
    if spawn_time is None:
        spawn_time = time.time()
    angle = math.atan2(ty - y, tx - x)
    vx = SHOT_SPEED * math.cos(angle)
    vy = SHOT_SPEED * math.sin(angle)
    shot = {
        'x': x,
        'y': y,
        'origin_x': x,
        'origin_y': y,
        'vx': vx,
        'vy': vy,
        'owner': owner_sid,
        'spawn_time': spawn_time,
    }
    shots.append(shot)

def interpolate_history(history, target_time):
    """
    Return interpolated position at target_time from history.
    """
    if not history:
        return None
    if target_time <= history[0]['t']:
        return {'x': history[0]['x'], 'y': history[0]['y']}
    for i in range(1, len(history)):
        prev = history[i-1]
        curr = history[i]
        if prev['t'] <= target_time <= curr['t']:
            alpha = (target_time - prev['t']) / (curr['t'] - prev['t'] + 1e-8)
            x = prev['x'] * (1 - alpha) + curr['x'] * alpha
            y = prev['y'] * (1 - alpha) + curr['y'] * alpha
            return {'x': x, 'y': y}
    return {'x': history[-1]['x'], 'y': history[-1]['y']}