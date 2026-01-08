from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state: mapping of session IDs to (x, y) positions
players = {}

BOX_WIDTH = 500
BOX_HEIGHT = 500
PLAYER_RADIUS = 20
MOVE_AMOUNT = 3
START_X = BOX_WIDTH // 2
START_Y = BOX_HEIGHT // 2

@app.route('/')
def index():
    return send_from_directory('../client', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('../client', path)

@socketio.on('connect')
def handle_connect():
    # Initialize player position at center
    players[request.sid] = {'x': START_X, 'y': START_Y}
    emit('state', players)  # Send all players to new client
    emit('state', players, broadcast=True)  # Update everyone

@socketio.on('move')
def handle_move(data):
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    pos = players.get(request.sid, {'x': START_X, 'y': START_Y})
    x = pos['x'] + dx * MOVE_AMOUNT
    y = pos['y'] + dy * MOVE_AMOUNT

    # Clamp to boundaries
    x = max(PLAYER_RADIUS, min(BOX_WIDTH - PLAYER_RADIUS, x))
    y = max(PLAYER_RADIUS, min(BOX_HEIGHT - PLAYER_RADIUS, y))

    players[request.sid] = {'x': x, 'y': y}
    emit('state', players, broadcast=True)  # Broadcast updated state

@socketio.on('disconnect')
def handle_disconnect():
    players.pop(request.sid, None)
    emit('state', players, broadcast=True)  # Broadcast updated state

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)