// client/main.js

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const PLAYER_WIDTH = 20;
const PLAYER_HEIGHT = 40;
const BOX_WIDTH = 500;
const BOX_HEIGHT = 500;

let playerX = BOX_WIDTH / 2;

// Connect to the server
const socket = io('http://localhost:5000');

// Listen for initial state or updates from server
socket.on('state', (data) => {
    if (data.x !== undefined) {
        playerX = data.x;
        draw();
    }
});

// Handle keyboard input (A/D)
document.addEventListener('keydown', (e) => {
    if (e.code === 'KeyA') {
        socket.emit('move', { direction: -1 });
    } else if (e.code === 'KeyD') {
        socket.emit('move', { direction: 1 });
    }
});

// Draw the game box and player
function draw() {
    ctx.clearRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Draw box border
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Draw player (simple rectangle)
    ctx.fillStyle = '#0074D9';
    ctx.fillRect(playerX, BOX_HEIGHT - PLAYER_HEIGHT - 10, PLAYER_WIDTH, PLAYER_HEIGHT);
}

// Initial draw
draw();

canvas.focus();