// client/main.js

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const PLAYER_RADIUS = 20;
const BOX_WIDTH = 500;
const BOX_HEIGHT = 500;
const GHOST_ALPHA = 0.4; // Transparency for ghost

let myId = null;
let players = {}; // { socketId: {x, y, ghost: {x, y}} }
let moveX = 0;
let moveY = 0;

// Connect to the server
const socket = io('http://localhost:5000');

// Listen for state updates from the server (sent continuously)
socket.on('state', (data) => {
    players = data;
    if (!myId) {
        myId = socket.id;
    }
    draw();
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

// Draw the game box and all players, including their ghosts
function draw() {
    ctx.clearRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Draw box border
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    for (const id in players) {
        const p = players[id];
        // Draw ghost
        if (p.ghost && typeof p.ghost.x === 'number' && typeof p.ghost.y === 'number') {
            ctx.save();
            ctx.globalAlpha = GHOST_ALPHA;
            ctx.beginPath();
            ctx.arc(p.ghost.x, p.ghost.y, PLAYER_RADIUS, 0, Math.PI * 2);
            ctx.fillStyle = id === myId ? '#0074D9' : '#FF4136';
            ctx.fill();
            ctx.globalAlpha = 1.0;
            ctx.restore();
        }
        // Draw player
        ctx.beginPath();
        ctx.arc(p.x, p.y, PLAYER_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = id === myId ? '#0074D9' : '#FF4136';
        ctx.fill();
    }
}

// Initial draw
draw();

// Start movement loop
movementLoop();

canvas.focus();