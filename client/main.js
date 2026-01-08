// client/main.js

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const PLAYER_WIDTH = 20;
const PLAYER_HEIGHT = 40;
const BOX_WIDTH = 500;
const BOX_HEIGHT = 500;

let playerX = BOX_WIDTH / 2;

// Continuous movement variables
let moveDirection = 0; // -1 for left, 1 for right, 0 for none
let moving = false;

// Connect to the server
const socket = io('http://localhost:5000');

// Listen for state updates from the server
socket.on('state', (data) => {
    if (data.x !== undefined) {
        playerX = data.x;
        draw();
    }
});

// Handle keyboard input for continuous movement
document.addEventListener('keydown', (e) => {
    if (e.code === 'KeyA' && moveDirection !== -1) {
        moveDirection = -1;
        sendMove();
    } else if (e.code === 'KeyD' && moveDirection !== 1) {
        moveDirection = 1;
        sendMove();
    }
});

document.addEventListener('keyup', (e) => {
    if ((e.code === 'KeyA' && moveDirection === -1) ||
        (e.code === 'KeyD' && moveDirection === 1)) {
        moveDirection = 0;
    }
});

// Send move request to server at an interval while key is held down
function movementLoop() {
    if (moveDirection !== 0) {
        sendMove();
    }
    requestAnimationFrame(movementLoop);
}

function sendMove() {
    socket.emit('move', { direction: moveDirection });
}

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

// Start movement loop
movementLoop();

canvas.focus();