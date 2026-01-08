// client/main.js

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const PLAYER_RADIUS = 20;
const BOX_WIDTH = 500;
const BOX_HEIGHT = 500;
const GHOST_ALPHA = 0.4; // Transparency for ghost
const SHOT_RADIUS = 5;

let myId = null;
let players = {}; // { socketId: {x, y, ghost: {x, y}, delay: number} }
let shots = [];   // [{x, y}]
let moveX = 0;
let moveY = 0;

// --- delay mechanic vars ---
let currentDelay = 0.5; // will be set from server state
let delayInc = false;
let delayDec = false;

// Connect to the server
const socket = io();

// Listen for state updates from the server (sent continuously)
socket.on('state', (data) => {
    // shots array is inside data.shots, others are player data
    shots = data.shots || [];
    delete data.shots;
    players = data;
    if (!myId) {
        myId = socket.id;
    }
    // Update my delay for display
    if (players[myId] && typeof players[myId].delay === "number") {
        currentDelay = players[myId].delay;
    }
    draw();
    updateDelayDisplay();
});

// Handle keyboard input for continuous movement and delay change
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
        case 'KeyK':
            socket.emit('shoot');
            break;
        case 'KeyL':
            if (!delayInc) {
                delayInc = true;
                socket.emit('delay_inc_start');
            }
            break;
        case 'KeyJ':
            if (!delayDec) {
                delayDec = true;
                socket.emit('delay_dec_start');
            }
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
        case 'KeyL':
            if (delayInc) {
                delayInc = false;
                socket.emit('delay_inc_stop');
            }
            break;
        case 'KeyJ':
            if (delayDec) {
                delayDec = false;
                socket.emit('delay_dec_stop');
            }
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
    delayDiv.innerText = `Current Ghost Delay: ${currentDelay.toFixed(3)}s (J/L to change)`;
}

// Initial draw
draw();

// Start movement loop
movementLoop();

canvas.focus();
