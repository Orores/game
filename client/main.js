// client/main.js

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const PLAYER_RADIUS = 20;
const BOX_WIDTH = 500;
const BOX_HEIGHT = 500;
const GHOST_ALPHA = 0.4;
const SHOT_RADIUS = 5;

let myId = null;
let players = {}; // { socketId: {x, y, ghost: {x, y}, delay: number, score: number} }
let shots = [];   // [{x, y}]
let moveX = 0;
let moveY = 0;

// Delay controls
let currentDelay = 0.5;
let delayInc = false;
let delayDec = false;

// Connect to server
const socket = io('http://localhost:5000');

// Receive state from server
socket.on('state', (data) => {
    shots = data.shots || [];
    delete data.shots;
    players = data;
    if (!myId) myId = socket.id;
    if (players[myId] && typeof players[myId].delay === "number")
        currentDelay = players[myId].delay;
    draw();
    updateDelayDisplay();
});

// --- Input handling ---
document.addEventListener('keydown', (e) => {
    switch (e.code) {
        case 'KeyA': moveX = -1; break;
        case 'KeyD': moveX = 1; break;
        case 'KeyW': moveY = -1; break;
        case 'KeyS': moveY = 1; break;
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
        case 'KeyA': if (moveX === -1) moveX = 0; break;
        case 'KeyD': if (moveX === 1) moveX = 0; break;
        case 'KeyW': if (moveY === -1) moveY = 0; break;
        case 'KeyS': if (moveY === 1) moveY = 0; break;
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

// Movement loop
function movementLoop() {
    if (moveX !== 0 || moveY !== 0) {
        socket.emit('move', { dx: moveX, dy: moveY });
    }
    requestAnimationFrame(movementLoop);
}

// Drawing function
function draw() {
    ctx.clearRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Box border
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, BOX_WIDTH, BOX_HEIGHT);

    // Shots
    ctx.fillStyle = "#222";
    for (const shot of shots) {
        ctx.beginPath();
        ctx.arc(shot.x, shot.y, SHOT_RADIUS, 0, Math.PI * 2);
        ctx.fill();
    }

    // Players and ghosts
    for (const id in players) {
        const p = players[id];
        // Ghost
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
        // Player
        ctx.beginPath();
        ctx.arc(p.x, p.y, PLAYER_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = id === myId ? '#0074D9' : '#FF4136';
        ctx.fill();

        ctx.fillStyle = "#000";
        ctx.font = "bold 16px Arial";
        ctx.textAlign = "center";
        ctx.fillText("Score: " + (p.score || 0), p.x, p.y - PLAYER_RADIUS - 10);
    }
}

// Delay UI
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

// Initial draw and start movement
draw();
movementLoop();
canvas.focus();