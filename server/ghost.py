# server/ghost.py

import time

# Ghost delay parameters
DEFAULT_GHOST_DELAY = 1.0  # seconds (initial delay per player)
MIN_GHOST_DELAY = 0.5      # minimum value in seconds
MAX_GHOST_DELAY = 1.5      # maximum value in seconds

def prune_history(history, now, max_age):
    """
    Prune the player's position history so it only contains entries within max_age seconds of 'now'.
    """
    return [h for h in history if now - h['t'] <= max_age]

def get_ghost_position(history, now, delay):
    """
    Given a history of positions and a delay, interpolate the ghost's position.
    Returns a dict with 'x' and 'y', or None if history is empty.
    """
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
