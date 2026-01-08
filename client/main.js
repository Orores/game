// client/main.js

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const PLAYER_RADIUS = 20;
const BOX_WIDTH = 500;
const BOX_HEIGHT = 500;
const GHOST_ALPHA = 0.4;
const SHOT_RADIUS = 5;

let myId = null;
let players = {};
let shots = [];
let moving = { left: false, right: false, up: false, down: false };
let delayMoving = { up: false, down: false }; // Space = up (increase), Middle mouse = down (decrease)

let currentDelay = 0.5;

// Mouse position relative to canvas
let mouseX = BOX_WIDTH / 2;
let mouseY = BOX_HEIGHT / 2;

// Connect to the server
const socket = io();

// Listen for state updates from the server (sent continuously)
socket.on('state', (data) => {
    shots = data.shots || [];
    delete data.shots;
    players = data;
    if (!myId) {
        myId = socket.id;
    }
    if (players[myId] && typeof players[myId].delay === "number") {
        currentDelay = players[myId].delay;
    }
    draw();
    updateDelayDisplay();
});

// Movement helpers
function emitMoveState(dir, state) {
    if (state) {
        socket.emit('move_start', { dir });
    } else {
        socket.emit('move_stop', { dir });
    }
}

// Delay helpers (for ghost delay control)
function emitDelayState(dir, state) {
    if (state) {
        socket.emit('delay_start', { dir });
    } else {
        socket.emit('delay_stop', { dir });
    }
}

// Handle keyboard input for movement and delay
document.addEventListener('keydown', (e) => {
    // Movement
    switch (e.code) {
        case 'KeyA':
            if (!moving.left) { moving.left = true; emitMoveState('left', true); }
            break;
        case 'KeyD':
            if (!moving.right) { moving.right = true; emitMoveState('right', true); }
            break;
        case 'KeyW':
            if (!moving.up) { moving.up = true; emitMoveState('up', true); }
            break;
        case 'KeyS':
            if (!moving.down) { moving.down = true; emitMoveState('down', true); }
            break;
    }

    // Delay control: Space for delay up
    if (e.code === 'Space') {
        if (!delayMoving.up) { delayMoving.up = true; emitDelayState('up', true); }
        e.preventDefault();
    }
});

document.addEventListener('keyup', (e) => {
    // Movement
    switch (e.code) {
        case 'KeyA':
            if (moving.left) { moving.left = false; emitMoveState('left', false); }
            break;
        case 'KeyD':
            if (moving.right) { moving.right = false; emitMoveState('right', false); }
            break;
        case 'KeyW':
            if (moving.up) { moving.up = false; emitMoveState('up', false); }
            break;
        case 'KeyS':
            if (moving.down) { moving.down = false; emitMoveState('down', false); }
            break;
    }

    // Delay control: Space for delay up
    if (e.code === 'Space') {
        if (delayMoving.up) { delayMoving.up = false; emitDelayState('up', false); }
        e.preventDefault();
    }
});

// --- Mouse targeting & shooting ---
canvas.addEventListener('mousemove', function(e) {
    const rect = canvas.getBoundingClientRect();
    mouseX = (e.clientX - rect.left) * (canvas.width / rect.width);
    mouseY = (e.clientY - rect.top) * (canvas.height / rect.height);
});

// Shoot on left mouse button
canvas.addEventListener('mousedown', function(e) {
    // e.button: 0=left, 1=middle, 2=right
    if (e.button === 0) {
        socket.emit('shoot', { x: mouseX, y: mouseY });
    }
    // Middle mouse button for delay down
    if (e.button === 1) {
        if (!delayMoving.down) {
            delayMoving.down = true;
            emitDelayState('down', true);
        }
        e.preventDefault();
    }
});

// Release middle mouse button for delay down
canvas.addEventListener('mouseup', function(e) {
    if (e.button === 1) {
        if (delayMoving.down) {
            delayMoving.down = false;
            emitDelayState('down', false);
        }
        e.preventDefault();
    }
});

// Prevent context menu on canvas for middle/right click
canvas.addEventListener('contextmenu', function(e) {
    e.preventDefault();
});

// Draw the game box, all players, their ghosts, and shots
function draw() {
    ctx.clearRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Draw box border
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Draw shots
    ctx.fillStyle = "#222";
    for (const shot of shots) {
        ctx.beginPath();
        ctx.arc(shot.x, shot.y, SHOT_RADIUS, 0, Math.PI * 2);
        ctx.fill();
    }

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

        // Draw score (above player)
        ctx.fillStyle = "#000";
        ctx.font = "bold 16px Arial";
        ctx.textAlign = "center";
        ctx.fillText("Score: " + (p.score || 0), p.x, p.y - PLAYER_RADIUS - 10);
    }
}

// --- Delay display ---
function updateDelayDisplay() {
    let delayDiv = document.getElementById('delay');
    if (!delayDiv) {
        delayDiv = document.createElement('div');
        delayDiv.id = 'delay';
        delayDiv.style.marginTop = '10px';
        delayDiv.style.fontSize = '1.1rem';
        delayDiv.style.fontWeight = 'bold';
        delayDiv.style.color = '#0074D9';
        delayDiv.style.textAlign = 'center';
        document.body.insertBefore(delayDiv, document.body.children[1]);
    }
    delayDiv.innerText = `Current Ghost Delay: ${currentDelay.toFixed(3)}s`;
}

// Initial draw
draw();

canvas.focus();