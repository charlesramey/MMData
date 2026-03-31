// ─────────────────────────────────────────────────────────────────────────────
// MMData Web Sync Tool  –  main.js
// Hardcoded data series: Accel Magnitude (Ax,Ay,Az), Gyro Magnitude (Gx,Gy,Gz),
// Pressure (raw scalar).  Time column auto-detected.
// ─────────────────────────────────────────────────────────────────────────────

// ── Obstacle Tooltips (mirrors desktop TOOLTIPS dict) ─────────────────────────
const TOOLTIPS = {
    jump: {
        stride_start: 'Jump STRIDE_START: First front paw contact that initiates the stride before the takeoff stride sequence (includes 8 paw strikes before last paw leaves ground).',
        obs_start:    'Jump OBS_START: Last paw leaves the ground for takeoff (should be a rear paw).',
        obs_stop:     'Jump OBS_STOP: First paw contacts the ground after the jump (should be a front paw).',
        stride_stop:  'Jump STRIDE_STOP: The last rear paw has left the ground of the stride following the landing stride (includes 8 paw strikes from first landing contact).'
    },
    tunnel: {
        stride_start: 'Tunnel STRIDE_START: First paw contact of the stride immediately before CORE_START.',
        obs_start:    'Tunnel OBS_START: Nose breaks the entry plane of the tunnel opening.',
        obs_stop:     'Tunnel OBS_STOP: Last paw fully clears the exit plane of the tunnel opening.',
        stride_stop:  'Tunnel STRIDE_STOP: Completion of the stride immediately after CORE_STOP (last paw off or next clear contact).'
    },
    teeter: {
        stride_start: 'Teeter STRIDE_START: First paw contact of the approach stride.',
        obs_start:    'Teeter OBS_START: Nose breaks the plane of the teeter entry.',
        obs_stop:     'Teeter OBS_STOP: Last paw leaves contact with the teeter board.',
        stride_stop:  'Teeter STRIDE_STOP: Completion of the stride after last paw leaves the board (after release).'
    },
    aframe: {
        stride_start: 'A-frame STRIDE_START: First paw contact of the approach stride.',
        obs_start:    'A-frame OBS_START: Nose breaks the entry plane/threshold of the A-frame.',
        obs_stop:     'A-frame OBS_STOP: Last paw leaves contact with the A-frame.',
        stride_stop:  'A-frame STRIDE_STOP: Completion of the stride after last paw leaves the A-frame.'
    },
    dogwalk: {
        stride_start: 'Dogwalk STRIDE_START: First paw contact of the approach stride.',
        obs_start:    'Dogwalk OBS_START: Nose breaks the entry plane of the dogwalk (start of up plank).',
        obs_stop:     'Dogwalk OBS_STOP: Last paw leaves contact with the dogwalk.',
        stride_stop:  'Dogwalk STRIDE_STOP: Completion of the stride after last paw leaves the dogwalk.'
    },
    weave: {
        stride_start: 'Weave STRIDE_START: First paw contact of the stride immediately before OBS_START.',
        obs_start:    'Weave OBS_START: First frame where the dog\'s nose breaks the plane of pole 1.',
        obs_stop:     'Weave OBS_STOP: Last paw crosses the plane of the last pole (pole 12).',
        stride_stop:  'Weave STRIDE_STOP: Completion of the stride immediately after OBS_STOP.'
    },
    flat: {
        stride_start: 'Generic STRIDE_START',
        obs_start:    'Generic OBS_START',
        obs_stop:     'Generic OBS_STOP',
        stride_stop:  'Generic STRIDE_STOP'
    }
};

// ── State ─────────────────────────────────────────────────────────────────────
let rootHandle    = null;
let filePairs     = [];
let currentIdx    = -1;
let syncLogHandle = null;
let globalAudioBuffer = null;
let isSaved       = true;   // tracks whether current file has been saved

// Plot settings (mirrors desktop defaults)
let showLPF     = true;
let lpfFreq     = 5.0;
let showSeries  = [true, true, true]; // accel, gyro, pressure

// Hardcoded column config – auto-detected per file from CSV headers
// Populated in detectColumnConfig()
let columnConfig = null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const btnOpenDir    = document.getElementById('btnOpenDir');
const btnNextFile   = document.getElementById('btnNextFile');
const lblCurrentFile= document.getElementById('lblCurrentFile');
const fileInput     = document.getElementById('fileInput');
const videoPlayer   = document.getElementById('videoPlayer');
const btnPlay       = document.getElementById('btnPlay');
const selSpeed      = document.getElementById('selSpeed');
const rngOffset     = document.getElementById('rngOffset');
const lblOffset     = document.getElementById('lblOffset');
const btnOffsetMinus= document.getElementById('btnOffsetMinus');
const btnOffsetPlus = document.getElementById('btnOffsetPlus');
const btnToggleSpec = document.getElementById('btnToggleSpec');
const btnPlotSettings= document.getElementById('btnPlotSettings');

let syncOffsetMs  = 30000;
let showSpectrogram = true;
let sensorChart   = null;

// ── Marker colours (match desktop) ───────────────────────────────────────────
const markerColors = {
    stride_start: '#448aff',
    obs_start:    '#69f0ae',
    obs_stop:     '#ff5252',
    stride_stop:  '#e040fb'
};

// ── Chart.js playhead plugin ──────────────────────────────────────────────────
const playheadPlugin = {
    id: 'playhead',
    afterDatasetsDraw(chart) {
        if (!videoPlayer || !chart.scales.x) return;
        const ctx  = chart.ctx;
        const area = chart.chartArea;
        const offsetSec = (syncOffsetMs - 30000) / 1000.0;

        const drawLine = (timeVal, color, lineWidth = 2, dashed = false) => {
            const x = chart.scales.x.getPixelForValue(timeVal);
            if (x < area.left || x > area.right) return;
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(x, area.top);
            ctx.lineTo(x, area.bottom);
            ctx.lineWidth = lineWidth;
            ctx.strokeStyle = color;
            ctx.setLineDash(dashed ? [5,5] : []);
            ctx.stroke();
            ctx.restore();
        };

        // Playhead
        drawLine(videoPlayer.currentTime + offsetSec, 'white', 2);

        // Markers
        for (const [key, ms] of Object.entries(marks)) {
            if (ms !== null) drawLine(ms / 1000.0 + offsetSec, markerColors[key] || 'yellow', 3);
        }
    }
};

// ── Init ──────────────────────────────────────────────────────────────────────
setupSplitters();
setupResizeObserver();

// ── Open Directory ────────────────────────────────────────────────────────────
btnOpenDir.addEventListener('click', async () => {
    if ('showDirectoryPicker' in window) {
        try {
            rootHandle = await window.showDirectoryPicker();
            filePairs  = [];
            await scanDirectory(rootHandle);
            finishScan();
        } catch (err) {
            console.error('Error opening directory:', err);
        }
    } else {
        fileInput.click();
    }
});

fileInput.addEventListener('change', e => {
    filePairs = scanFileList(Array.from(e.target.files));
    finishScan();
});

async function finishScan() {
    filePairs.sort((a, b) => a.dirName.localeCompare(b.dirName));
    if (filePairs.length === 0) { alert('No video/CSV pairs found.'); return; }

    currentIdx = 0;
    isSaved    = true;

    if (rootHandle) {
        rootHandle.getFileHandle('sync_log.csv', { create: true })
            .then(h => syncLogHandle = h)
            .catch(e => console.warn('Could not access sync_log.csv', e));
    }

    btnNextFile.disabled = filePairs.length <= 1;
    loadFile(0);
}

// ── Directory / File scanning ─────────────────────────────────────────────────
async function scanDirectory(dirHandle) {
    let videoHandle = null, csvHandle = null;
    for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file') {
            const n = entry.name.toLowerCase();
            if (!videoHandle && (n.endsWith('.mp4') || n.endsWith('.avi') || n.endsWith('.mov')))
                videoHandle = entry;
            else if (!csvHandle && n.endsWith('.csv') && n !== 'sync_log.csv')
                csvHandle = entry;
        } else if (entry.kind === 'directory') {
            await scanDirectory(entry);
        }
    }
    if (videoHandle && csvHandle) {
        filePairs.push({
            dirName: dirHandle.name,
            videoName: videoHandle.name,
            video: { getFile: () => videoHandle.getFile() },
            csv:   { getFile: () => csvHandle.getFile()   }
        });
    }
}

function scanFileList(files) {
    const dirs = {};
    files.forEach(f => {
        const parts   = (f.webkitRelativePath || f.name).split('/');
        const dirPath = parts.slice(0, -1).join('/');
        const dirName = parts.length > 1 ? parts[parts.length - 2] : 'root';
        if (!dirs[dirPath]) dirs[dirPath] = { video: null, videoName: null, csv: null, dirName };
        const n = f.name.toLowerCase();
        if (!dirs[dirPath].video && (n.endsWith('.mp4') || n.endsWith('.avi') || n.endsWith('.mov'))) {
            dirs[dirPath].video     = f;
            dirs[dirPath].videoName = f.name;
        } else if (!dirs[dirPath].csv && n.endsWith('.csv') && n !== 'sync_log.csv') {
            dirs[dirPath].csv = f;
        }
    });
    return Object.values(dirs)
        .filter(d => d.video && d.csv)
        .map(d => ({
            dirName:   d.dirName,
            videoName: d.videoName,
            video: { getFile: async () => d.video },
            csv:   { getFile: async () => d.csv   }
        }));
}

// ── Obstacle detection & tooltips ─────────────────────────────────────────────
function detectObstacle(path) {
    const p = path.toLowerCase();
    if (p.includes('jump'))    return 'jump';
    if (p.includes('tunnel'))  return 'tunnel';
    if (p.includes('teeter'))  return 'teeter';
    if (p.includes('weave'))   return 'weave';
    if (p.includes('dogwalk')) return 'dogwalk';
    if (p.includes('aframe') || p.includes('a-frame')) return 'aframe';
    return 'flat';
}

function updateTooltips(obsType) {
    const tips = TOOLTIPS[obsType] || TOOLTIPS.flat;
    const btnMap = {
        stride_start: document.getElementById('btnStrideStart'),
        obs_start:    document.getElementById('btnObsStart'),
        obs_stop:     document.getElementById('btnObsStop'),
        stride_stop:  document.getElementById('btnStrideStop')
    };
    for (const [key, btn] of Object.entries(btnMap)) {
        if (btn) btn.title = tips[key] || '';
    }
}

// ── Hardcoded column config auto-detection ────────────────────────────────────
// Series: Accel Magnitude (Ax,Ay,Az), Gyro Magnitude (Gx,Gy,Gz), Pressure (scalar)
// Time column: first column whose name contains "time" / "ts" / "timestamp"
function detectColumnConfig(headers) {
    const hl = headers.map(h => h.toLowerCase());

    // Time column
    let timeCol = headers.find((h, i) =>
        hl[i] === 'time' || hl[i] === 'ts' || hl[i] === 'timestamp' || hl[i].includes('time'));
    if (!timeCol) timeCol = headers[0]; // fallback to first column

    // Helper: find a header that starts with a given prefix (case-insensitive)
    const find = prefix => headers.find(h => h.toLowerCase().startsWith(prefix.toLowerCase())) || null;

    const series = [];

    // Series 1 – Accel Magnitude
    const ax = find('Ax'), ay = find('Ay'), az = find('Az');
    if (ax && ay && az) {
        series.push({ type: 'magnitude', x: ax, y: ay, z: az, label: 'Accel Mag' });
    }

    // Series 2 – Gyro Magnitude
    const gx = find('Gx'), gy = find('Gy'), gz = find('Gz');
    if (gx && gy && gz) {
        series.push({ type: 'magnitude', x: gx, y: gy, z: gz, label: 'Gyro Mag' });
    }

    // Series 3 – Pressure (scalar)
    const pressure = find('pressure') || find('baro') || find('press');
    if (pressure) {
        series.push({ type: 'raw', col: pressure, label: 'Pressure' });
    }

    return { timeCol, series };
}

// ── Load file ─────────────────────────────────────────────────────────────────
async function loadFile(idx) {
    const pair = filePairs[idx];
    const obsType = detectObstacle(pair.dirName);
    lblCurrentFile.textContent = `File: ${pair.dirName} (${obsType.toUpperCase()})`;
    updateTooltips(obsType);

    // Load video
    const vidFile = await pair.video.getFile();
    videoPlayer.src = URL.createObjectURL(vidFile);
    videoPlayer.playbackRate = parseFloat(selSpeed.value);

    // Load & parse CSV to detect columns (first time or per file)
    const csvFile  = await pair.csv.getFile();
    const csvText  = await csvFile.text();

    // Auto-detect column config from CSV headers
    const parseResult = Papa.parse(csvText, { header: true, preview: 1, skipEmptyLines: true });
    if (parseResult.meta && parseResult.meta.fields) {
        columnConfig = detectColumnConfig(parseResult.meta.fields);
    } else {
        console.error('Could not parse CSV headers');
        alert('Could not parse CSV headers.');
        return;
    }

    processCSV(csvText);
    setupSpectrogram(vidFile);

    // Reset offset
    syncOffsetMs    = 30000;
    rngOffset.value = 30000;
    lblOffset.textContent = '0 ms';

    clearMarks();
    updateCursor(0);

    isSaved = false;
}

// ── Next file (with unsaved-changes guard) ────────────────────────────────────
btnNextFile.addEventListener('click', () => {
    if (!isSaved) {
        if (!confirm('You have not saved your data for this file. Are you sure you want to advance to the next file?')) {
            return;
        }
    }
    if (currentIdx < filePairs.length - 1) {
        currentIdx++;
        isSaved = true; // reset before loading new
        loadFile(currentIdx);
    } else {
        alert('Done! All files processed.');
    }
});

// ── Splitters ─────────────────────────────────────────────────────────────────
function setupSplitters() {
    document.querySelectorAll('.splitter').forEach(splitter => {
        splitter.addEventListener('mousedown', e => {
            e.preventDefault();
            const prev = splitter.previousElementSibling;
            const next = splitter.nextElementSibling;
            if (!prev || !next) return;

            const startH = prev.getBoundingClientRect().height;
            const nextH  = next.getBoundingClientRect().height;
            const startY = e.clientY;

            prev.style.flex = `0 0 ${startH}px`;
            next.style.flex = `0 0 ${nextH}px`;
            splitter.classList.add('active');
            document.body.style.cursor = 'row-resize';

            const onMove = e => {
                e.preventDefault();
                const dy = e.clientY - startY;
                const np = startH + dy, nn = nextH - dy;
                if (np > 50 && nn > 50) {
                    prev.style.flexBasis = `${np}px`;
                    next.style.flexBasis = `${nn}px`;
                }
            };
            const onUp = () => {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                splitter.classList.remove('active');
                document.body.style.cursor = 'default';
                if (sensorChart) sensorChart.resize();
            };
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });
    });
}

function setupResizeObserver() {
    const obs = new ResizeObserver(() => {
        if (globalAudioBuffer) requestAnimationFrame(() => drawSpectrogram(globalAudioBuffer));
    });
    obs.observe(document.getElementById('spectrogram-container'));
}

// ── Playback controls ─────────────────────────────────────────────────────────
btnPlay.addEventListener('click', togglePlay);

function togglePlay() {
    if (videoPlayer.paused) {
        videoPlayer.play();
        btnPlay.textContent = '⏸ PAUSE';
    } else {
        videoPlayer.pause();
        btnPlay.textContent = '▶ PLAY';
    }
}

selSpeed.addEventListener('change', () => {
    videoPlayer.playbackRate = parseFloat(selSpeed.value);
});

rngOffset.addEventListener('input', () => {
    syncOffsetMs = parseInt(rngOffset.value);
    updateOffsetLabel();
    updateCursor(videoPlayer.currentTime * 1000);
});

btnOffsetMinus.addEventListener('click', () => {
    const v = Math.max(0, parseInt(rngOffset.value) - 1);
    rngOffset.value = v;
    syncOffsetMs = v;
    updateOffsetLabel();
    updateCursor(videoPlayer.currentTime * 1000);
});

btnOffsetPlus.addEventListener('click', () => {
    const v = Math.min(60000, parseInt(rngOffset.value) + 1);
    rngOffset.value = v;
    syncOffsetMs = v;
    updateOffsetLabel();
    updateCursor(videoPlayer.currentTime * 1000);
});

function updateOffsetLabel() {
    const d = syncOffsetMs - 30000;
    lblOffset.textContent = `${d > 0 ? '+' : ''}${d} ms`;
}

videoPlayer.addEventListener('timeupdate', () => {
    updateCursor(videoPlayer.currentTime * 1000);
});

// ── Toggle spectrogram ────────────────────────────────────────────────────────
btnToggleSpec.addEventListener('click', () => {
    showSpectrogram = !showSpectrogram;
    const cont  = document.getElementById('spectrogram-container');
    const split = document.getElementById('split-1');
    cont.style.display  = showSpectrogram ? 'flex'  : 'none';
    split.style.display = showSpectrogram ? 'block' : 'none';
    if (sensorChart) setTimeout(() => sensorChart.resize(), 50);
});

// ── Plot Settings Modal ───────────────────────────────────────────────────────
const plotSettingsModal = document.getElementById('plotSettingsModal');

btnPlotSettings.addEventListener('click', () => {
    // Sync modal checkboxes to current state
    document.getElementById('chkSeries1').checked = showSeries[0];
    document.getElementById('chkSeries2').checked = showSeries[1];
    document.getElementById('chkSeries3').checked = showSeries[2];
    document.getElementById('chkShowLPF').checked  = showLPF;
    document.getElementById('inpLPFFreq').value    = lpfFreq;
    plotSettingsModal.style.display = 'flex';
});

document.getElementById('btnPlotSettingsCancel').addEventListener('click', () => {
    plotSettingsModal.style.display = 'none';
});

document.getElementById('btnPlotSettingsApply').addEventListener('click', () => {
    const newShowSeries = [
        document.getElementById('chkSeries1').checked,
        document.getElementById('chkSeries2').checked,
        document.getElementById('chkSeries3').checked
    ];
    const newShowLPF = document.getElementById('chkShowLPF').checked;
    const newLPFFreq = parseFloat(document.getElementById('inpLPFFreq').value) || 5.0;

    const needsReprocess = newLPFFreq !== lpfFreq;

    showSeries = newShowSeries;
    showLPF    = newShowLPF;
    lpfFreq    = newLPFFreq;

    plotSettingsModal.style.display = 'none';

    // Re-render chart if a file is loaded
    if (columnConfig && currentIdx >= 0) {
        if (needsReprocess) {
            // Re-read and reprocess CSV
            filePairs[currentIdx].csv.getFile().then(f => f.text()).then(text => processCSV(text));
        } else {
            rebuildChart();
        }
    }
});

// Cached processed data for rebuildChart (no LPF change needed)
let _cachedLabels   = null;
let _cachedRawNorm  = []; // per series
let _cachedLPFNorm  = []; // per series

function rebuildChart() {
    if (!_cachedLabels || !columnConfig) return;

    const colors = ['#00bcd4', '#ff4081', '#ffb74d', '#76ff03', '#d500f9'];
    const datasets = [];

    columnConfig.series.forEach((series, idx) => {
        if (!showSeries[idx]) return;
        const color     = colors[idx % colors.length];
        const labelBase = series.label || `Series ${idx + 1}`;
        const rawNorm   = _cachedRawNorm[idx];
        const lpfNorm   = _cachedLPFNorm[idx];

        if (rawNorm) {
            datasets.push({
                label: `${labelBase} (Raw)`,
                data: rawNorm,
                borderColor: color,
                borderWidth: 1.5,
                pointRadius: 0,
                fill: false,
                tension: 0.1,
                order: 2
            });
        }

        if (showLPF && lpfNorm) {
            datasets.push({
                label: `${labelBase} (${lpfFreq}Hz LPF)`,
                data: lpfNorm,
                borderColor: color + '99',
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                tension: 0.1,
                order: 1
            });
        }
    });

    if (sensorChart) sensorChart.destroy();
    sensorChart = buildChart(_cachedLabels, datasets);
}

// ── Spectrogram ───────────────────────────────────────────────────────────────
let audioCtx  = null;
let specBuffer = null;
const specCanvas = document.getElementById('spectrogramCanvas');
const specCtx    = specCanvas.getContext('2d', { willReadFrequently: true });

async function setupSpectrogram(file) {
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const ab          = await file.arrayBuffer();
        const audioBuffer = await audioCtx.decodeAudioData(ab);
        globalAudioBuffer = audioBuffer;
        drawSpectrogram(audioBuffer);
    } catch (e) {
        console.error('Audio processing failed', e);
        globalAudioBuffer = null;
    }
}

function fft(real, imag) {
    const n = real.length;
    let j = 0;
    for (let i = 0; i < n; i++) {
        if (i < j) {
            [real[i], real[j]] = [real[j], real[i]];
            [imag[i], imag[j]] = [imag[j], imag[i]];
        }
        let m = n >> 1;
        while (m >= 1 && j >= m) { j -= m; m >>= 1; }
        j += m;
    }
    for (let step = 1; step < n; step <<= 1) {
        const jump = step << 1;
        const da   = -Math.PI / step;
        const sinD = Math.sin(da), cosD = Math.cos(da);
        let sinA = 0, cosA = 1;
        for (let grp = 0; grp < step; grp++) {
            for (let i = grp; i < n; i += jump) {
                const k = i + step;
                const tr = cosA * real[k] - sinA * imag[k];
                const ti = cosA * imag[k] + sinA * real[k];
                real[k] = real[i] - tr; imag[k] = imag[i] - ti;
                real[i] += tr;          imag[i] += ti;
            }
            const tc = cosA * cosD - sinA * sinD;
            sinA = cosA * sinD + sinA * cosD;
            cosA = tc;
        }
    }
}

function drawSpectrogram(buffer) {
    if (!buffer) return;
    const W = specCanvas.clientWidth || 800;
    const H = specCanvas.clientHeight || 150;
    specCanvas.width  = W;
    specCanvas.height = H;

    const data       = buffer.getChannelData(0);
    const fftSize    = 512;
    const sampleRate = buffer.sampleRate;
    const maxFreq    = 10000;
    const maxBin     = Math.floor(maxFreq / (sampleRate / fftSize));
    const binsToDraw = Math.min(maxBin, fftSize / 2);

    specCtx.fillStyle = 'black';
    specCtx.fillRect(0, 0, W, H);

    const real     = new Float32Array(fftSize);
    const imag     = new Float32Array(fftSize);
    const win      = new Float32Array(fftSize);
    for (let i = 0; i < fftSize; i++) win[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (fftSize - 1)));

    const imgData = specCtx.createImageData(W, H);
    const pixels  = imgData.data;

    for (let x = 0; x < W; x++) {
        const offset = Math.floor(x * (data.length - fftSize) / W);
        if (offset < 0) continue;
        for (let i = 0; i < fftSize; i++) {
            real[i] = (offset + i < data.length ? data[offset + i] : 0) * win[i];
            imag[i] = 0;
        }
        fft(real, imag);

        for (let y = 0; y < H; y++) {
            const binIdx = Math.floor((1 - y / H) * binsToDraw);
            const mag    = Math.sqrt(real[binIdx] ** 2 + imag[binIdx] ** 2);
            const db     = 20 * Math.log10(mag + 1e-10);
            const norm   = Math.max(0, Math.min(1, (db + 80) / 80));
            const pi     = (y * W + x) * 4;
            // Inferno-like palette
            pixels[pi]     = Math.floor(norm < 0.5 ? norm * 2 * 150   : 150 + (norm - 0.5) * 2 * 105);
            pixels[pi + 1] = Math.floor(norm < 0.5 ? norm * 2 * 30    : 30  + (norm - 0.5) * 2 * 195);
            pixels[pi + 2] = Math.floor(norm < 0.5 ? 50 + norm * 2 * 80 : 130 - (norm - 0.5) * 2 * 130);
            pixels[pi + 3] = 255;
        }
    }

    specCtx.putImageData(imgData, 0, 0);
    specBuffer = specCtx.getImageData(0, 0, W, H);
}

function drawSpectrogramCursor(t_ms) {
    if (!specBuffer) return;
    specCtx.putImageData(specBuffer, 0, 0);
    const dur = videoPlayer.duration * 1000;
    if (dur > 0) {
        const x = (t_ms / dur) * specCanvas.width;
        specCtx.beginPath();
        specCtx.strokeStyle = 'white';
        specCtx.lineWidth   = 2;
        specCtx.moveTo(x, 0);
        specCtx.lineTo(x, specCanvas.height);
        specCtx.stroke();
    }
}

// ── DSP helpers ───────────────────────────────────────────────────────────────
function calculateMagnitude(x, y, z) {
    return x.map((v, i) => Math.sqrt(v * v + y[i] * y[i] + z[i] * z[i]));
}

function normalizeData(arr) {
    const mn = Math.min(...arr), mx = Math.max(...arr);
    if (mx === mn) return arr.map(() => 0);
    return arr.map(v => (v - mn) / (mx - mn));
}

function lowPassFilter(data, fs, cutoff) {
    const omega0  = 2 * Math.PI * cutoff / fs;
    const sinO    = Math.sin(omega0), cosO = Math.cos(omega0);
    const alpha   = sinO / (2 * 0.7071);
    const b0 = (1 - cosO) / 2, b1 = 1 - cosO, b2 = (1 - cosO) / 2;
    const a0 = 1 + alpha,  a1 = -2 * cosO, a2 = 1 - alpha;
    const B0 = b0/a0, B1 = b1/a0, B2 = b2/a0, A1 = a1/a0, A2 = a2/a0;
    const y = new Array(data.length).fill(0);
    for (let i = 0; i < data.length; i++) {
        y[i] = B0 * data[i]
             + B1 * (i > 0 ? data[i-1] : 0)
             + B2 * (i > 1 ? data[i-2] : 0)
             - A1 * (i > 0 ? y[i-1]    : 0)
             - A2 * (i > 1 ? y[i-2]    : 0);
    }
    return y;
}

// ── CSV processing ────────────────────────────────────────────────────────────
function processCSV(text) {
    if (!columnConfig) { console.error('No column config'); return; }

    const results = Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true });
    const data    = results.data;
    if (!data || data.length < 2) { console.error('Invalid CSV'); return; }

    const timeCol  = columnConfig.timeCol;
    const timestamps = data.map(r => r[timeCol]);
    if (timestamps.some(t => t == null)) {
        alert(`Time column "${timeCol}" not found in this file.`); return;
    }

    const t0     = timestamps[0];
    const labels = timestamps.map(t => t - t0);
    const dur    = timestamps[timestamps.length - 1] - t0 || 1;
    const fs     = data.length / dur;

    // Process and cache each series
    _cachedLabels  = labels;
    _cachedRawNorm = [];
    _cachedLPFNorm = [];

    const colors   = ['#00bcd4', '#ff4081', '#ffb74d', '#76ff03', '#d500f9'];
    const datasets = [];

    columnConfig.series.forEach((series, idx) => {
        let rawData;
        if (series.type === 'raw') {
            rawData = data.map(r => r[series.col] || 0);
        } else {
            rawData = calculateMagnitude(
                data.map(r => r[series.x] || 0),
                data.map(r => r[series.y] || 0),
                data.map(r => r[series.z] || 0)
            );
        }

        const normRaw = normalizeData(rawData);
        const lpfData = lowPassFilter(rawData, fs, lpfFreq);
        const normLPF = normalizeData(lpfData);

        _cachedRawNorm[idx] = normRaw;
        _cachedLPFNorm[idx] = normLPF;

        if (!showSeries[idx]) return;

        const color     = colors[idx % colors.length];
        const labelBase = series.label || `Series ${idx + 1}`;

        datasets.push({
            label: `${labelBase} (Raw)`,
            data: normRaw,
            borderColor: color,
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0.1,
            order: 2
        });

        if (showLPF) {
            datasets.push({
                label: `${labelBase} (${lpfFreq}Hz LPF)`,
                data: normLPF,
                borderColor: color + '99',
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                tension: 0.1,
                order: 1
            });
        }
    });

    if (sensorChart) sensorChart.destroy();
    sensorChart = buildChart(labels, datasets);
}

function buildChart(labels, datasets) {
    const canvas = document.getElementById('sensorCanvas');
    return new Chart(canvas, {
        type: 'line',
        data: { labels, datasets },
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
                    grid:  { color: '#333' },
                    ticks: { color: '#888' }
                },
                y: {
                    grid:  { color: '#333' },
                    title: { display: true, text: 'Normalized', color: '#888' },
                    ticks: { color: '#888' },
                    min: 0, max: 1.1
                }
            },
            plugins: {
                legend:  { labels: { color: 'white' } },
                tooltip: { mode: 'index', intersect: false }
            }
        },
        plugins: [playheadPlugin]
    });
}

// ── Cursor update ─────────────────────────────────────────────────────────────
function updateCursor(t_ms) {
    drawSpectrogramCursor(t_ms);
    if (sensorChart) sensorChart.update('none');
}

// ── Markers ───────────────────────────────────────────────────────────────────
let marks = { stride_start: null, obs_start: null, obs_stop: null, stride_stop: null };

document.getElementById('btnStrideStart').addEventListener('click', () => addMark('stride_start'));
document.getElementById('btnObsStart').addEventListener('click',   () => addMark('obs_start'));
document.getElementById('btnObsStop').addEventListener('click',    () => addMark('obs_stop'));
document.getElementById('btnStrideStop').addEventListener('click', () => addMark('stride_stop'));
document.getElementById('btnClear').addEventListener('click', clearMarks);
document.getElementById('btnSave').addEventListener('click', saveData);

function addMark(key) {
    if (!videoPlayer.src) return;
    marks[key] = Math.round(videoPlayer.currentTime * 1000);
    if (sensorChart) sensorChart.update('none');
}

function clearMarks() {
    marks = { stride_start: null, obs_start: null, obs_stop: null, stride_stop: null };
    document.getElementById('chkAbnormal').checked = false;
    if (sensorChart) sensorChart.update('none');
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function saveData() {
    if (currentIdx === -1) { alert('No file loaded.'); return; }

    const pair    = filePairs[currentIdx];
    const rowData = {
        Timestamp:     new Date().toISOString().replace('T', ' ').substring(0, 19),
        Computer_Name: navigator.userAgent.match(/\(([^)]+)\)/)?.[1]?.split(';')[0]?.trim() || 'Web',
        Directory:     pair.dirName,
        Video_File:    pair.videoName || '',
        CSV_File:      '',          // not tracked in web (file handle only)
        Offset_ms:     syncOffsetMs - 30000,
        Start_ms:      marks.stride_start ?? '',
        Stop_ms:       marks.stride_stop  ?? '',
        Incomplete:    '',
        Missed_Contact:'',
        Duration_s:    (marks.stride_start != null && marks.stride_stop != null)
                         ? ((marks.stride_stop - marks.stride_start) / 1000).toFixed(3)
                         : '',
        Notes:         '',
        stride_start:  marks.stride_start ?? '',
        obs_start:     marks.obs_start    ?? '',
        obs_stop:      marks.obs_stop     ?? '',
        stride_stop:   marks.stride_stop  ?? '',
        Abnormal:      document.getElementById('chkAbnormal').checked
    };

    const values = Object.values(rowData).map(v => v === null || v === undefined ? '' : v);
    const line   = values.join(',') + '\n';

    if (syncLogHandle) {
        try {
            const writable = await syncLogHandle.createWritable({ keepExistingData: true });
            const file     = await syncLogHandle.getFile();
            await writable.write({ type: 'write', position: file.size, data: line });
            await writable.close();
            isSaved = true;
            alert('Saved!');
            // Auto-advance to next file
            if (currentIdx < filePairs.length - 1) {
                currentIdx++;
                isSaved = true;
                loadFile(currentIdx);
            }
        } catch (e) {
            console.error('Save failed', e);
            alert('Save failed: ' + e.message);
        }
    } else {
        // Fallback – download individual entry
        const blob = new Blob([line], { type: 'text/csv' });
        const url  = URL.createObjectURL(blob);
        const a    = Object.assign(document.createElement('a'), { href: url, download: `sync_log_entry_${pair.dirName}.csv` });
        a.click();
        URL.revokeObjectURL(url);
        isSaved = true;
        alert('Log entry downloaded (Fallback Mode).');
        if (currentIdx < filePairs.length - 1) {
            currentIdx++;
            isSaved = true;
            loadFile(currentIdx);
        }
    }
}

// ── Keyboard shortcuts (Space, S, D, F, G) ────────────────────────────────────
document.addEventListener('keydown', e => {
    // Don't fire when user is typing in an input
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    switch (e.code) {
        case 'Space': e.preventDefault(); togglePlay();          break;
        case 'KeyS':  addMark('stride_start');                   break;
        case 'KeyD':  addMark('obs_start');                      break;
        case 'KeyF':  addMark('obs_stop');                       break;
        case 'KeyG':  addMark('stride_stop');                    break;
    }
});