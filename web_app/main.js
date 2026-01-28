
// State
let rootHandle = null;
let filePairs = [];
let currentIdx = -1;
let syncLogHandle = null;
let globalAudioBuffer = null;

// DOM Elements
const btnOpenDir = document.getElementById('btnOpenDir');
const btnNextFile = document.getElementById('btnNextFile');
const lblCurrentFile = document.getElementById('lblCurrentFile');
const fileInput = document.getElementById('fileInput');

// Playhead & Marker Plugin for Chart.js
const markerColors = {
    stride_start: '#448aff',
    obs_start: '#69f0ae',
    obs_stop: '#ff5252',
    stride_stop: '#e040fb'
};

const playheadPlugin = {
    id: 'playhead',
    afterDatasetsDraw: (chart) => {
        if (!videoPlayer) return;

        const ctx = chart.ctx;
        const area = chart.chartArea;
        const top = area.top;
        const bottom = area.bottom;

        // Ensure x scale exists
        if (!chart.scales.x) return;

        // Apply sync offset (syncOffsetMs is centered at 30000)
        // Offset = (Slider - 30000) ms
        const offsetSec = (syncOffsetMs - 30000) / 1000.0;

        // Helper function to draw vertical line
        const drawLine = (timeVal, color, lineWidth = 2, isDashed = false) => {
            const x = chart.scales.x.getPixelForValue(timeVal);
            if (x < area.left || x > area.right) return;

            ctx.save();
            ctx.beginPath();
            ctx.moveTo(x, top);
            ctx.lineTo(x, bottom);
            ctx.lineWidth = lineWidth;
            ctx.strokeStyle = color;
            if (isDashed) ctx.setLineDash([5, 5]);
            else ctx.setLineDash([]);
            ctx.stroke();
            ctx.restore();
        };

        // 1. Draw Playhead
        const currentTime = videoPlayer.currentTime; // seconds
        drawLine(currentTime + offsetSec, 'white', 2, false);

        // 2. Draw Markers
        for (const [key, ms] of Object.entries(marks)) {
            if (ms !== null) {
                const sec = ms / 1000.0;
                // Markers are on video timeline, so shift by offset to match chart
                drawLine(sec + offsetSec, markerColors[key] || 'yellow', 3, false);
            }
        }
    }
};

// Setup
setupSplitters();
setupResizeObserver();

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

    // Setup Audio Context for Spectrogram
    setupSpectrogram(vidFile);

    // Reset Sync Offset to 0ms (Slider center = 30000)
    syncOffsetMs = 30000;
    rngOffset.value = 30000;
    lblOffset.textContent = "0 ms";

    // Clear marks
    clearMarks();

    // Update cursor immediately
    updateCursor(0);
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

// Splitter & Layout Logic
function setupSplitters() {
    const splitters = document.querySelectorAll('.splitter');
    splitters.forEach(splitter => {
        splitter.addEventListener('mousedown', initDrag);
    });

    function initDrag(e) {
        e.preventDefault();
        const splitter = e.target;
        const prev = splitter.previousElementSibling;
        const next = splitter.nextElementSibling;

        if (!prev || !next) return;

        // Get initial heights
        const prevRect = prev.getBoundingClientRect();
        const nextRect = next.getBoundingClientRect();
        const startH = prevRect.height;
        const nextH = nextRect.height;
        const startY = e.clientY;

        // Switch to fixed sizing (flex-basis) to control precise pixels
        // flex: 0 0 basis
        prev.style.flex = `0 0 ${startH}px`;
        next.style.flex = `0 0 ${nextH}px`;

        splitter.classList.add('active');
        document.body.style.cursor = 'row-resize';

        function onMouseMove(e) {
            e.preventDefault();
            const dy = e.clientY - startY;
            const newPrevH = startH + dy;
            const newNextH = nextH - dy;

            // Min height constraint (e.g. 50px)
            if (newPrevH > 50 && newNextH > 50) {
                prev.style.flexBasis = `${newPrevH}px`;
                next.style.flexBasis = `${newNextH}px`;
            }
        }

        function onMouseUp() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            splitter.classList.remove('active');
            document.body.style.cursor = 'default';

            // Ensure Chart resizes if involved
            if (sensorChart) sensorChart.resize();
        }

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }
}

function setupResizeObserver() {
    const container = document.getElementById('spectrogram-container');
    const resizeObserver = new ResizeObserver(entries => {
        if (globalAudioBuffer) {
            // Debounce or just request frame
            requestAnimationFrame(() => drawSpectrogram(globalAudioBuffer));
        }
    });
    resizeObserver.observe(container);
}

// Playback Logic
const videoPlayer = document.getElementById('videoPlayer');
const btnPlay = document.getElementById('btnPlay');
const selSpeed = document.getElementById('selSpeed');
const rngOffset = document.getElementById('rngOffset');
const lblOffset = document.getElementById('lblOffset');
const btnToggleSpec = document.getElementById('btnToggleSpec');

let isPlaying = false;
let syncOffsetMs = 30000;
let showSpectrogram = true;

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
    const offsetDisplay = syncOffsetMs - 30000;
    lblOffset.textContent = `${offsetDisplay > 0 ? '+' : ''}${offsetDisplay} ms`;
    updateCursor(videoPlayer.currentTime * 1000);
});

videoPlayer.addEventListener('timeupdate', () => {
    const t_ms = videoPlayer.currentTime * 1000;
    updateCursor(t_ms);
});

if (btnToggleSpec) {
    btnToggleSpec.addEventListener('click', () => {
        showSpectrogram = !showSpectrogram;
        const container = document.getElementById('spectrogram-container');
        const split1 = document.getElementById('split-1'); // The splitter above it

        if (showSpectrogram) {
            container.style.display = 'flex';
            split1.style.display = 'block';
        } else {
            container.style.display = 'none';
            split1.style.display = 'none';
        }

        // Trigger resize for neighbors
        if (sensorChart) setTimeout(() => sensorChart.resize(), 50);
    });
}

// Spectrogram Logic
let audioCtx = null;
let specBuffer = null;
const specCanvas = document.getElementById('spectrogramCanvas');
const specCtx = specCanvas.getContext('2d', { willReadFrequently: true });

async function setupSpectrogram(file) {
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const arrayBuffer = await file.arrayBuffer();
        const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);

        globalAudioBuffer = audioBuffer;

        // Draw Spectrogram
        drawSpectrogram(audioBuffer);
    } catch (e) {
        console.error("Audio processing failed", e);
        globalAudioBuffer = null;
    }
}

// Simple FFT Implementation (Radix-2)
function fft(real, imag) {
    const n = real.length;
    if (n === 0) return;
    if ((n & (n - 1)) !== 0) throw new Error("FFT length must be power of 2");

    // Bit-reversal
    let j = 0;
    for (let i = 0; i < n; i++) {
        if (i < j) {
            [real[i], real[j]] = [real[j], real[i]];
            [imag[i], imag[j]] = [imag[j], imag[i]];
        }
        let m = n >> 1;
        while (m >= 1 && j >= m) {
            j -= m;
            m >>= 1;
        }
        j += m;
    }

    // Butterfly
    for (let step = 1; step < n; step <<= 1) {
        const jump = step << 1;
        const deltaAngle = -Math.PI / step;
        const sinDelta = Math.sin(deltaAngle);
        const cosDelta = Math.cos(deltaAngle);

        let sinAlpha = 0;
        let cosAlpha = 1; // cos(0)

        for (let grp = 0; grp < step; grp++) {
            for (let i = grp; i < n; i += jump) {
                const k = i + step;
                const tReal = cosAlpha * real[k] - sinAlpha * imag[k];
                const tImag = cosAlpha * imag[k] + sinAlpha * real[k];
                real[k] = real[i] - tReal;
                imag[k] = imag[i] - tImag;
                real[i] += tReal;
                imag[i] += tImag;
            }
            // Update angles
            const tempCos = cosAlpha * cosDelta - sinAlpha * sinDelta;
            sinAlpha = cosAlpha * sinDelta + sinAlpha * cosDelta;
            cosAlpha = tempCos;
        }
    }
}

function drawSpectrogram(buffer) {
    if (!buffer) return;

    // Set canvas internal size to match display size for sharpness
    const displayWidth = specCanvas.clientWidth || 800;
    const displayHeight = specCanvas.clientHeight || 150;

    specCanvas.width = displayWidth;
    specCanvas.height = displayHeight;

    const data = buffer.getChannelData(0);
    const canvasWidth = specCanvas.width;
    const canvasHeight = specCanvas.height;

    // Parameters
    const fftSize = 512; // Frequency resolution (256 bins)

    // Limits
    const sampleRate = buffer.sampleRate; // e.g., 44100 or 48000
    const nyquist = sampleRate / 2;
    const maxFreq = 10000; // Cap at 10kHz

    // Calculate how many bins cover 0 to maxFreq
    // Bin resolution = sampleRate / fftSize
    // Index = freq / (sampleRate / fftSize)
    const binResolution = sampleRate / fftSize;
    const maxBinIndex = Math.floor(maxFreq / binResolution);

    // Total bins to check (limit by maxFreq or Nyquist)
    const totalBins = fftSize / 2;
    const binsToDraw = Math.min(maxBinIndex, totalBins);

    // Draw background
    specCtx.fillStyle = 'black';
    specCtx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Helper arrays for FFT
    const real = new Float32Array(fftSize);
    const imag = new Float32Array(fftSize);
    const windowFunc = new Float32Array(fftSize);
    for(let i=0; i<fftSize; i++) windowFunc[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (fftSize - 1))); // Hanning

    // Optimization: Create ImageData and manipulate pixels directly
    const imgData = specCtx.createImageData(canvasWidth, canvasHeight);
    const pixels = imgData.data;

    for (let x = 0; x < canvasWidth; x++) {
        // Calculate the center sample index for this pixel column
        const offset = Math.floor(x * (data.length - fftSize) / canvasWidth);
        if (offset < 0) continue;

        // Prepare Window
        for (let i = 0; i < fftSize; i++) {
            // Guard against out of bounds
            const val = (offset + i < data.length) ? data[offset + i] : 0;
            real[i] = val * windowFunc[i];
            imag[i] = 0;
        }

        // Compute FFT
        fft(real, imag);

        // Compute Magnitude & Draw

        for (let y = 0; y < canvasHeight; y++) {
            // Map y (0 is top = maxFreq) to frequency bin (0 is DC)
            // Normal mapping: y=0 -> Nyquist
            // New mapping: y=0 -> maxFreq (10kHz)

            // Invert y: y=0 is top, y=height is bottom (0Hz)
            const normalizedY = 1 - (y / canvasHeight); // 0 to 1 (0Hz to MaxFreq)
            const binIdx = Math.floor(normalizedY * binsToDraw);

            if (binIdx < 0 || binIdx >= binsToDraw) continue;

            const mag = Math.sqrt(real[binIdx]**2 + imag[binIdx]**2);
            // Log scale for magnitude
            const db = 20 * Math.log10(mag + 1e-6);

            // Normalize for visualization: -80dB to 0dB roughly
            // Adjust contrast here
            let val = (db + 80) / 80;
            if (val < 0) val = 0;
            if (val > 1) val = 1;

            // Color Mapping: Black -> Blue -> Red -> Yellow -> White
            let r=0, g=0, b=0;
            if (val < 0.25) {
                const t = val / 0.25;
                r=0; g=0; b=Math.floor(255*t);
            } else if (val < 0.5) {
                const t = (val-0.25)/0.25;
                r=Math.floor(255*t); g=0; b=Math.floor(255*(1-t));
            } else if (val < 0.75) {
                const t = (val-0.5)/0.25;
                r=255; g=Math.floor(255*t); b=0;
            } else {
                const t = (val-0.75)/0.25;
                r=255; g=255; b=Math.floor(255*t);
            }

            const pixIdx = (y * canvasWidth + x) * 4;
            pixels[pixIdx] = r;
            pixels[pixIdx+1] = g;
            pixels[pixIdx+2] = b;
            pixels[pixIdx+3] = 255; // Alpha
        }
    }

    specCtx.putImageData(imgData, 0, 0);
    specBuffer = specCtx.getImageData(0, 0, canvasWidth, canvasHeight);
}


// Sensor Plotting Logic
let sensorChart = null;
const sensorCanvas = document.getElementById('sensorCanvas');

// --- SIGNAL PROCESSING HELPERS ---

function calculateMagnitude(xArr, yArr, zArr) {
    return xArr.map((v, i) => Math.sqrt(v**2 + yArr[i]**2 + zArr[i]**2));
}

function normalizeData(arr) {
    let min = Infinity;
    let max = -Infinity;
    for (let v of arr) {
        if (v < min) min = v;
        if (v > max) max = v;
    }
    const range = max - min;
    if (range === 0) return arr.map(() => 0.5);
    return arr.map(v => (v - min) / range);
}

function lowPassFilter(data, fs, cutoff) {
    if (cutoff >= fs / 2) return data;

    const omega0 = 2 * Math.PI * cutoff / fs;
    const sinOmega0 = Math.sin(omega0);
    const cosOmega0 = Math.cos(omega0);
    const Q = 0.7071;
    const alpha_bi = sinOmega0 / (2 * Q);

    const b0 = (1 - cosOmega0) / 2;
    const b1 = 1 - cosOmega0;
    const b2 = (1 - cosOmega0) / 2;
    const a0 = 1 + alpha_bi;
    const a1 = -2 * cosOmega0;
    const a2 = 1 - alpha_bi;

    const b0n = b0 / a0;
    const b1n = b1 / a0;
    const b2n = b2 / a0;
    const a1n = a1 / a0;
    const a2n = a2 / a0;

    const y = new Array(data.length).fill(0);

    for (let i = 0; i < data.length; i++) {
        const x_0 = data[i];
        const x_1 = i > 0 ? data[i-1] : 0;
        const x_2 = i > 1 ? data[i-2] : 0;
        const y_1 = i > 0 ? y[i-1] : 0;
        const y_2 = i > 1 ? y[i-2] : 0;

        y[i] = b0n * x_0 + b1n * x_1 + b2n * x_2 - a1n * y_1 - a2n * y_2;
    }

    return y;
}

function processCSV(text) {
    const results = Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true });
    const data = results.data;

    if (!data || data.length < 2) {
        console.error("Invalid or empty CSV");
        return;
    }

    const headers = Object.keys(data[0]);
    const hasGyro = headers.includes('Gx') && headers.includes('Gy') && headers.includes('Gz');

    const timestamps = data.map(r => r.Timestamp);
    const t0 = timestamps[0];
    const t1 = timestamps[timestamps.length - 1];

    let duration = t1 - t0;
    const startT = t0;
    const labels = timestamps.map(t => (t - startT));

    const count = timestamps.length;
    let avgDiff = duration / count;
    if (avgDiff === 0 || isNaN(avgDiff)) avgDiff = 0.01;
    const fs = 1.0 / avgDiff;
    console.log(`Detected fs: ${fs.toFixed(2)} Hz`);

    const ax = data.map(r => r.Ax || 0);
    const ay = data.map(r => r.Ay || 0);
    const az = data.map(r => r.Az || 0);

    let gx = [], gy = [], gz = [];
    if (hasGyro) {
        gx = data.map(r => r.Gx || 0);
        gy = data.map(r => r.Gy || 0);
        gz = data.map(r => r.Gz || 0);
    }

    let magAccel = calculateMagnitude(ax, ay, az);
    let magGyro = hasGyro ? calculateMagnitude(gx, gy, gz) : [];

    // Normalize Raw
    let normAccelRaw = normalizeData(magAccel);
    let normGyroRaw = hasGyro ? normalizeData(magGyro) : [];

    const cutoff = 5;
    let magAccelLPF = lowPassFilter(magAccel, fs, cutoff);
    let magGyroLPF = hasGyro ? lowPassFilter(magGyro, fs, cutoff) : [];

    let normAccel = normalizeData(magAccelLPF);
    let normGyro = hasGyro ? normalizeData(magGyroLPF) : [];

    if (sensorChart) sensorChart.destroy();

    const datasets = [
        {
            label: 'Accel Mag (Raw)',
            data: normAccelRaw,
            borderColor: '#00bcd4',
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            tension: 0.1,
            borderDash: [3, 3],
            order: 2
        },
        {
            label: 'Accel Mag (5Hz LPF)',
            data: normAccel,
            borderColor: '#00bcd4',
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.1,
            order: 1
        }
    ];

    if (hasGyro) {
        datasets.push({
            label: 'Gyro Mag (Raw)',
            data: normGyroRaw,
            borderColor: '#ff4081',
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            tension: 0.1,
            borderDash: [3, 3],
            order: 2
        });
        datasets.push({
            label: 'Gyro Mag (5Hz LPF)',
            data: normGyro,
            borderColor: '#ff4081',
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.1,
            order: 1
        });
    }

    sensorChart = new Chart(sensorCanvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    type: 'linear',
                    display: true,
                    title: { display: true, text: 'Time (s)', color: '#888' },
                    grid: { color: '#333' },
                    ticks: { color: '#888' }
                },
                y: {
                    grid: { color: '#333' },
                    title: { display: true, text: 'Normalized Mag', color: '#888' },
                    ticks: { color: '#888' },
                    min: 0,
                    max: 1.1
                }
            },
            plugins: {
                legend: { labels: { color: 'white' } },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        },
        plugins: [playheadPlugin]
    });
}

function updateCursor(t_ms) {
    drawSpectrogramCursor(t_ms);
    // Trigger Chart Playhead Update
    if (sensorChart) {
        sensorChart.update('none'); // Efficient update without full animation
    }
}

function drawSpectrogramCursor(t_ms) {
    if (!specBuffer) return;
    specCtx.putImageData(specBuffer, 0, 0);

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

// Marker Logic
let marks = {
    stride_start: null, obs_start: null, obs_stop: null, stride_stop: null
};

document.querySelectorAll('.marker-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const id = e.target.id;
        const key = id.replace('btn', '').replace(/([A-Z])/g, '_$1').toLowerCase().substring(1);
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
    if (sensorChart) sensorChart.update('none');
}

function clearMarks() {
    marks = { stride_start: null, obs_start: null, obs_stop: null, stride_stop: null };
    console.log("Marks cleared");
    if (sensorChart) sensorChart.update('none');
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
        Offset_ms: syncOffsetMs - 30000,
        ...marks,
        Abnormal: document.getElementById('chkAbnormal').checked
    };

    const values = Object.values(rowData).map(v => v === null ? '' : v);
    const line = values.join(',') + '\n';

    if (syncLogHandle) {
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
