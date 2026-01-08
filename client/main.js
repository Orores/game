// client/main.js

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const PLAYER_RADIUS = 20;
const BOX_WIDTH = 500;
const BOX_HEIGHT = 500;

let playerX = BOX_WIDTH / 2;
let playerY = BOX_HEIGHT / 2;

// Movement direction
let moveX = 0; // -1 for left, 1 for right, 0 for none
let moveY = 0; // -1 for up, 1 for down, 0 for none

// Connect to the server
const socket = io('http://localhost:5000');

// Listen for state updates from the server
socket.on('state', (data) => {
    if (data.x !== undefined && data.y !== undefined) {
        playerX = data.x;
        playerY = data.y;
        draw();
    }
});

// Handle keyboard input for continuous movement
document.addEventListener('keydown', (e) => {
    switch (e.code) {
        case 'KeyA':
            moveX = -1;
            break;
        case 'KeyD':
            moveX = 1;
            break;
        case 'KeyW':
            moveY = -1;
            break;
        case 'KeyS':
            moveY = 1;
            break;
    }
});

document.addEventListener('keyup', (e) => {
    switch (e.code) {
        case 'KeyA':
            if (moveX === -1) moveX = 0;
            break;
        case 'KeyD':
            if (moveX === 1) moveX = 0;
            break;
        case 'KeyW':
            if (moveY === -1) moveY = 0;
            break;
        case 'KeyS':
            if (moveY === 1) moveY = 0;
            break;
    }
});

// Send move request to server on each animation frame
function movementLoop() {
    if (moveX !== 0 || moveY !== 0) {
        socket.emit('move', { dx: moveX, dy: moveY });
    }
    requestAnimationFrame(movementLoop);
}

// Draw the game box and player
function draw() {
    ctx.clearRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Draw box border
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Draw player as a circle
    ctx.fillStyle = '#0074D9';
    ctx.beginPath();
    ctx.arc(playerX, playerY, PLAYER_RADIUS, 0, Math.PI * 2);
    ctx.fill();
}

// Initial draw
draw();

// Start movement loop
movementLoop();

canvas.focus();