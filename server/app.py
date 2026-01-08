from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
# Use default async_mode ('threading') for maximum compatibility
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state: mapping of session IDs to player positions
players = {}

BOX_WIDTH = 500
PLAYER_WIDTH = 20
MOVE_AMOUNT = 10
START_X = BOX_WIDTH // 2

@app.route('/')
def index():
    return send_from_directory('../client', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    # Serve static files (JS, CSS) from client folder
    return send_from_directory('../client', path)

@socketio.on('connect')
def handle_connect():
    # Initialize player position at center
    players[request.sid] = START_X
    emit('state', {'x': players[request.sid]})

@socketio.on('move')
def handle_move(data):
    # data['direction'] should be -1 (left) or 1 (right)
    direction = data.get('direction', 0)
    x = players.get(request.sid, START_X)
    x += direction * MOVE_AMOUNT
    # Boundaries
    x = max(0, min(BOX_WIDTH - PLAYER_WIDTH, x))
    players[request.sid] = x
    emit('state', {'x': x})

@socketio.on('disconnect')
def handle_disconnect():
    players.pop(request.sid, None)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)