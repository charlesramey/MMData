
// State
let rootHandle = null;
let filePairs = [];
let currentIdx = -1;
let syncLogHandle = null;

// DOM Elements
const btnOpenDir = document.getElementById('btnOpenDir');
const btnNextFile = document.getElementById('btnNextFile');
const lblCurrentFile = document.getElementById('lblCurrentFile');
const fileInput = document.getElementById('fileInput');

// Setup
btnOpenDir.addEventListener('click', async () => {
    if ('showDirectoryPicker' in window) {
        try {
            rootHandle = await window.showDirectoryPicker();
            filePairs = [];
            await scanDirectory(rootHandle);
            finishScan();
        } catch (err) {
            console.error("Error opening directory:", err);
        }
    } else {
        // Fallback
        fileInput.click();
    }
});

fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    filePairs = scanFileList(files);
    finishScan();
});

function finishScan() {
    filePairs.sort((a, b) => a.dirName.localeCompare(b.dirName));
    if (filePairs.length > 0) {
        currentIdx = 0;
        // In fallback mode, syncLogHandle remains null
        if (rootHandle) {
            rootHandle.getFileHandle('sync_log.csv', { create: true })
                .then(h => syncLogHandle = h)
                .catch(e => console.warn("Could not access sync_log.csv", e));
        }
        loadFile(currentIdx);
        btnNextFile.disabled = filePairs.length <= 1;
    } else {
        alert("No video/CSV pairs found.");
    }
}

btnNextFile.addEventListener('click', () => {
    if (currentIdx < filePairs.length - 1) {
        currentIdx++;
        loadFile(currentIdx);
    } else {
        alert("Done! All files processed.");
    }
});

// Native FS API Scan
async function scanDirectory(dirHandle, path = "") {
    let videoHandle = null;
    let csvHandle = null;

    for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file') {
            const name = entry.name.toLowerCase();
            if (name.endsWith('.mp4') || name.endsWith('.avi') || name.endsWith('.mov')) {
                if (!videoHandle) videoHandle = entry;
            } else if (name.endsWith('.csv') && name !== 'sync_log.csv') {
                if (!csvHandle) csvHandle = entry;
            }
        } else if (entry.kind === 'directory') {
            await scanDirectory(entry, path + entry.name + "/");
        }
    }

    if (videoHandle && csvHandle) {
        // Wrapper for getFile()
        filePairs.push({
            dirName: dirHandle.name,
            video: { getFile: () => videoHandle.getFile() },
            csv: { getFile: () => csvHandle.getFile() },
            path: path
        });
    }
}

// Input Element Scan
function scanFileList(files) {
    const pairs = [];
    const dirs = {};

    // Group by directory path
    files.forEach(f => {
        const path = f.webkitRelativePath || f.name;
        const parts = path.split('/');
        const dirPath = parts.slice(0, -1).join('/');
        const dirName = parts.length > 1 ? parts[parts.length - 2] : 'root';

        if (!dirs[dirPath]) dirs[dirPath] = { video: null, csv: null, dirName: dirName };

        const name = f.name.toLowerCase();
        if (name.endsWith('.mp4') || name.endsWith('.avi') || name.endsWith('.mov')) {
            dirs[dirPath].video = f;
        } else if (name.endsWith('.csv') && name !== 'sync_log.csv') {
            dirs[dirPath].csv = f;
        }
    });

    for (const d of Object.values(dirs)) {
        if (d.video && d.csv) {
            pairs.push({
                dirName: d.dirName,
                video: { getFile: async () => d.video },
                csv: { getFile: async () => d.csv }
            });
        }
    }
    return pairs;
}

async function loadFile(idx) {
    const pair = filePairs[idx];
    lblCurrentFile.textContent = `File: ${pair.dirName} (${detectObstacle(pair.dirName)})`;

    // Load Video
    const vidFile = await pair.video.getFile();
    const vidURL = URL.createObjectURL(vidFile);
    const videoPlayer = document.getElementById('videoPlayer');
    videoPlayer.src = vidURL;
    videoPlayer.playbackRate = parseFloat(document.getElementById('selSpeed').value);

    // Load CSV Data
    const csvFile = await pair.csv.getFile();
    const csvText = await csvFile.text();
    processCSV(csvText);

    // Setup Audio Context for Spectrogram (re-using video audio)
    setupSpectrogram(vidFile);

    // Clear marks
    clearMarks();
}

function detectObstacle(path) {
    const p = path.toLowerCase();
    if (p.includes('jump')) return 'JUMP';
    if (p.includes('tunnel')) return 'TUNNEL';
    if (p.includes('teeter')) return 'TEETER';
    if (p.includes('weave')) return 'WEAVE';
    if (p.includes('dogwalk')) return 'DOGWALK';
    if (p.includes('aframe') || p.includes('a-frame')) return 'AFRAME';
    return 'FLAT';
}

// Playback Logic
const videoPlayer = document.getElementById('videoPlayer');
const btnPlay = document.getElementById('btnPlay');
const selSpeed = document.getElementById('selSpeed');
const rngOffset = document.getElementById('rngOffset');

let isPlaying = false;
let syncOffsetMs = 30000;

btnPlay.addEventListener('click', () => {
    if (videoPlayer.paused) {
        videoPlayer.play();
        btnPlay.textContent = "⏸ PAUSE";
    } else {
        videoPlayer.pause();
        btnPlay.textContent = "▶ PLAY";
    }
});

selSpeed.addEventListener('change', () => {
    videoPlayer.playbackRate = parseFloat(selSpeed.value);
});

rngOffset.addEventListener('input', () => {
    syncOffsetMs = parseInt(rngOffset.value);
    drawPlots(); // Redraw cursor
});

videoPlayer.addEventListener('timeupdate', () => {
    // Update cursors on plots
    const t_ms = videoPlayer.currentTime * 1000;
    updateCursor(t_ms);
});

// Spectrogram Logic
let audioCtx = null;
let specBuffer = null;
const specCanvas = document.getElementById('spectrogramCanvas');
const specCtx = specCanvas.getContext('2d');

async function setupSpectrogram(file) {
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const arrayBuffer = await file.arrayBuffer();
        const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);

        // Compute Spectrogram Image (Simplified)
        // For a real app, we'd use an OfflineAudioContext + AnalyserNode or a JS FFT library.
        // Doing full FFT in JS for a large file can be slow on the main thread.
        // Here we will just draw a dummy waveform for visualization proof-of-concept
        // OR implement a basic block-based FFT.

        drawWaveform(audioBuffer);
    } catch (e) {
        console.error("Audio processing failed", e);
    }
}

function drawWaveform(buffer) {
    const data = buffer.getChannelData(0);
    const step = Math.ceil(data.length / specCanvas.width);
    const amp = specCanvas.height / 2;

    specCtx.fillStyle = 'black';
    specCtx.fillRect(0, 0, specCanvas.width, specCanvas.height);
    specCtx.beginPath();
    specCtx.strokeStyle = '#00bcd4';

    for (let i = 0; i < specCanvas.width; i++) {
        let min = 1.0;
        let max = -1.0;
        for (let j = 0; j < step; j++) {
            const datum = data[i * step + j];
            if (datum < min) min = datum;
            if (datum > max) max = datum;
        }
        specCtx.moveTo(i, (1 + min) * amp);
        specCtx.lineTo(i, (1 + max) * amp);
    }
    specCtx.stroke();

    // Store image for redraw
    specBuffer = specCtx.getImageData(0, 0, specCanvas.width, specCanvas.height);
}

function drawSpectrogramCursor(t_ms) {
    if (!specBuffer) return;
    specCtx.putImageData(specBuffer, 0, 0);

    // Calculate X position based on time
    // This assumes canvas width maps to full duration.
    // For scrolling, we'd need more logic.
    const duration = videoPlayer.duration * 1000;
    if (duration > 0) {
        const x = (t_ms / duration) * specCanvas.width;
        specCtx.beginPath();
        specCtx.strokeStyle = 'white';
        specCtx.lineWidth = 2;
        specCtx.moveTo(x, 0);
        specCtx.lineTo(x, specCanvas.height);
        specCtx.stroke();
    }
}

// Sensor Plotting Logic
let sensorChart = null;
const sensorCanvas = document.getElementById('sensorCanvas');

function processCSV(text) {
    const results = Papa.parse(text, { header: true, dynamicTyping: true });
    const data = results.data;

    // Check columns
    if (!data[0] || !data[0].Timestamp || !data[0].Ax) {
        console.error("Invalid CSV format");
        return;
    }

    // Prepare Chart Data
    // We downsample for performance if needed, or use a scatterGL library.
    // Chart.js might struggle with huge datasets, but for <30s it should be fine (~3000 pts).

    const startT = data[0].Timestamp;
    const labels = data.map(r => (r.Timestamp - startT) * 1000); // Relative time in ms
    const mag = data.map(r => Math.sqrt(r.Ax**2 + r.Ay**2 + r.Az**2));

    if (sensorChart) sensorChart.destroy();

    sensorChart = new Chart(sensorCanvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Accel Mag',
                data: mag,
                borderColor: '#00bcd4',
                borderWidth: 1,
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: { mode: 'nearest', axis: 'x', intersect: false },
            scales: {
                x: {
                    type: 'linear',
                    display: true,
                    grid: { color: '#444' }
                },
                y: {
                    grid: { color: '#444' }
                }
            },
            plugins: {
                legend: { labels: { color: 'white' } }
            }
        }
    });
}

function updateCursor(t_ms) {
    drawSpectrogramCursor(t_ms);
    // Note: Chart.js annotation plugin is needed for efficient vertical lines,
    // or we draw on top. For now, we rely on hover interaction or simple updates.
}

// Marker & Data Saving Logic
let marks = {
    stride_start: null, obs_start: null, obs_stop: null, stride_stop: null
};

document.querySelectorAll('.marker-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const id = e.target.id;
        const key = id.replace('btn', '').replace(/([A-Z])/g, '_$1').toLowerCase().substring(1); // btnStrideStart -> stride_start
        addMark(key);
    });
});

document.getElementById('btnClear').addEventListener('click', clearMarks);
document.getElementById('btnSave').addEventListener('click', saveData);

function addMark(key) {
    if (!videoPlayer) return;
    const t_ms = videoPlayer.currentTime * 1000;
    marks[key] = Math.round(t_ms);
    console.log(`Marked ${key} at ${t_ms}ms`);
    // Ideally verify visually (not implemented in this PoC)
}

function clearMarks() {
    marks = { stride_start: null, obs_start: null, obs_stop: null, stride_stop: null };
    console.log("Marks cleared");
}

async function saveData() {
    if (currentIdx === -1) {
        alert("No file loaded.");
        return;
    }

    const pair = filePairs[currentIdx];
    const rowData = {
        Timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        Directory: pair.dirName,
        Offset_ms: syncOffsetMs,
        ...marks,
        Abnormal: document.getElementById('chkAbnormal').checked
    };

    const values = Object.values(rowData).map(v => v === null ? '' : v);
    const line = values.join(',') + '\n';

    if (syncLogHandle) {
        // Use File System Access API
        try {
            const writable = await syncLogHandle.createWritable({ keepExistingData: true });
            const file = await syncLogHandle.getFile();
            const size = file.size;
            await writable.write({ type: 'write', position: size, data: line });
            await writable.close();
            alert("Saved!");
            btnNextFile.click();
        } catch (e) {
            console.error("Save failed", e);
            alert("Save failed: " + e.message);
        }
    } else {
        // Fallback: Download the line as a snippet or full CSV (simplified to alert download)
        // In a real scenario, we'd append to a memory buffer and download the full log at the end.
        const blob = new Blob([line], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sync_log_entry_${pair.dirName}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        alert("Log entry downloaded (Fallback Mode).");
        btnNextFile.click();
    }
}
