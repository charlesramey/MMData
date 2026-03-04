import pandas as pd
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QMessageBox, QFileDialog, QLineEdit, QSplitter,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsLineItem, QComboBox, QCheckBox,
    QDialog, QTableWidget, QTableWidgetItem, QDialogButtonBox, QRadioButton, QButtonGroup,
    QFormLayout, QGroupBox, QGridLayout, QScrollArea, QFrame, QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QPen, QColor
from PyQt5.QtCore import Qt, QTimer, QSize, QSettings
import sys
import subprocess
import os
import csv
import platform  
import time      
from datetime import datetime
from scipy.signal import butter, filtfilt, spectrogram
from scipy.io import wavfile
import matplotlib.cm as cm
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from mmdata_utils import find_video_csv_pair, ensure_audio_extracted

# --- CONFIGURATION ---
DOWNSCALED_VIDEO_PREFIX = 'downscaled_720p_v3_'
OFFSET_RANGE_MS = 30000 
VIDEO_SIZE = (620, 440) 

# --- TOOLTIPS ---
TOOLTIPS = {
    'jump': {
        'obs_start': "<b>Jump OBS_START:</b> Last paw leaves the ground for takeoff (should be a rear paw).",
        'obs_stop': "<b>Jump OBS_STOP:</b> First paw contacts the ground after the jump (should be a front paw).",
        'stride_start': "<b>Jump STRIDE_START:</b> First front paw contact that initiates the stride before the takeoff stride sequence.<br>(Includes 8 paw strikes before last paw leaves ground).",
        'stride_stop': "<b>Jump STRIDE_STOP:</b> The last rear paw has left the ground of the stride following the landing stride.<br>(Includes 8 paw strikes from first landing contact)."
    },
    'tunnel': {
        'obs_start': "<b>Tunnel OBS_START:</b> Nose breaks the entry plane of the tunnel opening.",
        'obs_stop': "<b>Tunnel OBS_STOP:</b> Last paw fully clears the exit plane of the tunnel opening.",
        'stride_start': "<b>Tunnel STRIDE_START:</b> First paw contact of the stride immediately before CORE_START.",
        'stride_stop': "<b>Tunnel STRIDE_STOP:</b> Completion of the stride immediately after CORE_STOP (last paw off or next clear contact)."
    },
    'teeter': {
        'obs_start': "<b>Teeter OBS_START:</b> Nose breaks the plane of the teeter entry.",
        'obs_stop': "<b>Teeter OBS_STOP:</b> Last paw leaves contact with the teeter board.",
        'stride_start': "<b>Teeter STRIDE_START:</b> First paw contact of the approach stride.",
        'stride_stop': "<b>Teeter STRIDE_STOP:</b> Completion of the stride after last paw leaves the board (after release)."
    },
    'aframe': {
        'obs_start': "<b>A-frame OBS_START:</b> Nose breaks the entry plane/threshold of the A-frame.",
        'obs_stop': "<b>A-frame OBS_STOP:</b> Last paw leaves contact with the A-frame.",
        'stride_start': "<b>A-frame STRIDE_START:</b> First paw contact of the approach stride.",
        'stride_stop': "<b>A-frame STRIDE_STOP:</b> Completion of the stride after last paw leaves the A-frame."
    },
    'dogwalk': {
        'obs_start': "<b>Dogwalk OBS_START:</b> Nose breaks the entry plane of the dogwalk (start of up plank).",
        'obs_stop': "<b>Dogwalk OBS_STOP:</b> Last paw leaves contact with the dogwalk.",
        'stride_start': "<b>Dogwalk STRIDE_START:</b> First paw contact of the approach stride.",
        'stride_stop': "<b>Dogwalk STRIDE_STOP:</b> Completion of the stride after last paw leaves the dogwalk."
    },
    'weave': {
        'obs_start': "<b>Weave OBS_START:</b> First frame where the dog's nose breaks the plane of pole 1.",
        'obs_stop': "<b>Weave OBS_STOP:</b> Last paw crosses the plane of the last pole (pole 12).",
        'stride_start': "<b>Weave STRIDE_START:</b> First paw contact of the stride immediately before OBS_START.",
        'stride_stop': "<b>Weave STRIDE_STOP:</b> Completion of the stride immediately after OBS_STOP."
    },
    'flat': { # Fallback or specific flat definition if needed
         'obs_start': "Generic OBS_START", 'obs_stop': "Generic OBS_STOP",
         'stride_start': "Generic STRIDE_START", 'stride_stop': "Generic STRIDE_STOP"
    }
}
# ---------------------

if platform.system() == 'Darwin':  # macOS
    LOG_DIR = os.path.expanduser("~/Documents/DogAgilityLogs")
else: # Windows/Other
    LOG_DIR = os.getcwd()

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'sync_log.csv')
# ---------------------

STYLE_SHEET = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}
QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}
QLabel {
    color: #cccccc;
    font-weight: bold;
}
QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    min-height: 25px;
}
QPushButton:hover {
    background-color: #484b4d;
    border-color: #666666;
}
QPushButton:pressed {
    background-color: #505355;
}
QSlider::groove:horizontal {
    border: 1px solid #3d3d3d;
    height: 6px;
    background: #3d3d3d;
    margin: 2px 0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00bcd4;
    border: 1px solid #00bcd4;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSplitter::handle {
    background-color: #444444;
}
"""

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def apply_lowpass(data, cutoff, fs, order=4):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    if normal_cutoff >= 1: normal_cutoff = 0.99
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

def load_data(csv_path, config):
    try:
        df = pd.read_csv(csv_path)
        if df.empty: return None, "CSV file is empty."
    except Exception as e: return None, f"Error loading CSV: {e}"

    time_col = config.get('time_col')
    if time_col not in df.columns:
        return None, f"Error: Time column '{time_col}' not found."

    df['Relative_Time_s'] = df[time_col] - df[time_col].iloc[0]
    df['Relative_Time_ms'] = df['Relative_Time_s'] * 1000

    # Pre-calculate series data
    # We will store them in df as 'S1_Raw', 'S1_LPF', etc.
    # config['series'] is a list of dicts

    fs = 1.0 / np.mean(np.diff(df['Relative_Time_s'])) if len(df) > 1 else 100.0

    for i, series in enumerate(config['series']):
        idx = i + 1
        raw_data = None

        if series['type'] == 'raw':
            col = series['col']
            if col in df.columns:
                raw_data = df[col].values
        else: # magnitude
            x, y, z = series['x'], series['y'], series['z']
            if x in df.columns and y in df.columns and z in df.columns:
                raw_data = np.sqrt(df[x]**2 + df[y]**2 + df[z]**2)

        if raw_data is not None:
            # Normalize Raw
            norm_raw = (raw_data - np.min(raw_data)) / (np.max(raw_data) - np.min(raw_data)) if np.max(raw_data) > np.min(raw_data) else raw_data

            # LPF
            lpf_data = apply_lowpass(raw_data, 5.0, fs)
            # Normalize LPF
            norm_lpf = (lpf_data - np.min(lpf_data)) / (np.max(lpf_data) - np.min(lpf_data)) if np.max(lpf_data) > np.min(lpf_data) else lpf_data

            df[f'Series{idx}_Raw'] = norm_raw
            df[f'Series{idx}_LPF'] = norm_lpf

    return df, None

def find_closest_data_index(df, target_time_ms):
    time_series = df['Relative_Time_ms'].values
    idx = np.searchsorted(time_series, target_time_ms, side="left")
    if idx == 0: return 0
    if idx == len(df): return len(df) - 1
    return idx if abs(time_series[idx-1] - target_time_ms) > abs(time_series[idx] - target_time_ms) else idx - 1

class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None):
        plt.style.use('dark_background')
        fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#1e1e1e')
        super().__init__(fig)
        self.setParent(parent)
        self.reset_marker_objects()
        plt.tight_layout(pad=0.25)

    def reset_marker_objects(self):
        self.point_marker, = self.ax.plot([], [], 'o', color='#ff5252', markersize=6, zorder=10)
        self.playhead_line = self.ax.axvline(x=0, color='white', lw=1.5, zorder=5) # Playhead line
        # Use 0 instead of np.nan to avoid singular matrix errors during transform
        self.m = {
            'stride_start': (self.ax.axvline(x=1, color='#448aff', ls='--', alpha=0), self.ax.text(0,0,'',color='#448aff',fontsize=8,fontweight='bold', alpha=0)),
            'obs_start': (self.ax.axvline(x=1, color='#69f0ae', ls=':', alpha=0), self.ax.text(0,0,'',color='#69f0ae',fontsize=8,fontweight='bold', alpha=0)),
            'obs_stop': (self.ax.axvline(x=1, color='#ff5252', ls=':', alpha=0), self.ax.text(0,0,'',color='#ff5252',fontsize=8,fontweight='bold', alpha=0)),
            'stride_stop': (self.ax.axvline(x=1, color='#e040fb', ls='--', alpha=0), self.ax.text(0,0,'',color='#e040fb',fontsize=8,fontweight='bold', alpha=0))
        }

    def clear_markers(self):
        for line, label in self.m.values():
            line.set_xdata([np.nan]); line.set_alpha(0); label.set_alpha(0)
        self.point_marker.set_data([], [])
        self.playhead_line.set_xdata([0])
        self.draw()

    def update_data(self, df, config):
        self.df = df
        self.ax.clear()
        self.ax.set_facecolor('#1e1e1e')

        # Colors: Cyan, Pink, Orange, Green
        colors = ['#00bcd4', '#ff4081', '#ffb74d', '#76ff03']

        for i, series in enumerate(config['series']):
            idx = i + 1
            color = colors[i % len(colors)]
            label_base = series.get('label', f'Series {idx}')

            raw_key = f'Series{idx}_Raw'
            lpf_key = f'Series{idx}_LPF'

            if raw_key in df.columns:
                self.ax.plot(df['Relative_Time_s'], df[raw_key], color=color, lw=1.0, label=f'{label_base} (Raw)')

            if lpf_key in df.columns:
                self.ax.plot(df['Relative_Time_s'], df[lpf_key], color=color, lw=0.8, alpha=0.6, label=f'{label_base} (5Hz LPF)')

        self.ax.tick_params(colors='#e0e0e0')
        self.ax.xaxis.label.set_color('#e0e0e0')
        self.ax.yaxis.label.set_color('#e0e0e0')
        for spine in self.ax.spines.values():
            spine.set_color('#555555')
        self.ax.grid(True, ls='--', alpha=0.2, color='#555555')
        self.reset_marker_objects()
        self.ax.legend(fontsize=7, loc='upper left', framealpha=0.2, facecolor='#2b2b2b', edgecolor='#555555', labelcolor='white')
        self.draw()

    def set_marker(self, key, time_ms, offset_ms):
        line, label = self.m[key]
        time_s = (time_ms + offset_ms) / 1000.0
        line.set_xdata([time_s]); line.set_alpha(1.0)
        label.set_position((time_s, self.ax.get_ylim()[1])); label.set_text(key.upper().replace('_', ' ')); label.set_alpha(1.0)
        self.draw()

    def update_cursor(self, t_ms, offset_ms):
        if self.df is None: return
        current_time_s = (t_ms + offset_ms) / 1000.0
        idx = find_closest_data_index(self.df, t_ms + offset_ms)

        # Update Playhead Line
        self.playhead_line.set_xdata([current_time_s])

        # We need a robust Y value for the cursor point.
        y_val = 0.5
        if 'Series1_LPF' in self.df.columns:
            y_val = self.df.loc[idx, 'Series1_LPF']

        self.point_marker.set_data([self.df.loc[idx, 'Relative_Time_s']], [y_val])
        self.draw()

class SpectrogramCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.cursor_line = None
        self.pixmap_item = None

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(150)

        self.px_per_s = 1.0
        self.t_min = 0.0
        self.t_max = 1.0
        self.spectrogram_data = None

    def update_data(self, audio_path):
        self.scene.clear()
        self.cursor_line = None
        self.spectrogram_data = None

        if not audio_path or not os.path.exists(audio_path):
             self.scene.addText("No Audio")
             return

        try:
            fs, data = wavfile.read(audio_path)
            if len(data.shape) > 1: data = data.mean(axis=1)

            f, t, Sxx = spectrogram(data, fs, nperseg=1024, noverlap=512)
            Sxx = 10 * np.log10(Sxx + 1e-10)

            vmin, vmax = Sxx.min(), Sxx.max()
            Sxx_norm = (Sxx - vmin) / (vmax - vmin)

            rgba = cm.inferno(Sxx_norm)
            rgba = (rgba * 255).astype(np.uint8)
            rgba = np.flipud(rgba).copy()

            h, w, ch = rgba.shape
            bytes_per_line = ch * w

            self.spectrogram_data = rgba

            qimg = QImage(self.spectrogram_data.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimg)

            self.pixmap_item = self.scene.addPixmap(pixmap)

            pen = QPen(QColor(255, 255, 255))
            pen.setWidth(2)
            self.cursor_line = self.scene.addLine(0, 0, 0, h, pen)
            self.cursor_line.setZValue(10)

            self.t_min = t[0]
            self.t_max = t[-1]
            duration_s = self.t_max - self.t_min

            self.px_per_s = w / duration_s if duration_s > 0 else 1.0

            self.setSceneRect(0, 0, w, h)

            if self.viewport().height() > 0:
                scale_y = self.viewport().height() / h
                self.resetTransform()
                self.scale(1.0, scale_y)

        except Exception as e:
            print(f"Error computing spectrogram: {e}")
            self.scene.addText(f"Error: {e}")

    def update_cursor(self, t_ms):
        if not self.cursor_line: return
        t_s = t_ms / 1000.0

        if t_s < self.t_min: x = 0
        elif t_s > self.t_max: x = (self.t_max - self.t_min) * self.px_per_s
        else: x = (t_s - self.t_min) * self.px_per_s

        h = self.scene.height()
        self.cursor_line.setLine(x, 0, x, h)
        self.centerOn(x, h/2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene.height() > 0:
            scale_y = self.viewport().height() / self.scene.height()
            self.resetTransform()
            self.scale(1.0, scale_y)
            if self.cursor_line:
                 x = self.cursor_line.line().x1()
                 self.centerOn(x, self.scene.height()/2)

class ColumnSelectionDialog(QDialog):
    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Data Columns")
        self.resize(900, 600)
        self.csv_path = csv_path
        self.headers = []
        self.preview_data = []
        self.result_config = None

        main_layout = QVBoxLayout(self)

        # 1. Preview
        preview_group = QGroupBox("CSV Preview (First 5 Rows)")
        preview_layout = QVBoxLayout()
        self.table = QTableWidget()
        preview_layout.addWidget(self.table)
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)

        # 2. Config
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()

        # Time
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Time Column:"))
        self.time_combo = QComboBox()
        time_layout.addWidget(self.time_combo)
        config_layout.addLayout(time_layout)

        # Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_group = QButtonGroup(self)
        self.radio_raw = QRadioButton("Raw Columns")
        self.radio_mag = QRadioButton("Vector Magnitude (X,Y,Z)")
        self.radio_raw.setChecked(True)
        self.mode_group.addButton(self.radio_raw)
        self.mode_group.addButton(self.radio_mag)
        mode_layout.addWidget(self.radio_raw)
        mode_layout.addWidget(self.radio_mag)
        mode_layout.addStretch()
        config_layout.addLayout(mode_layout)

        # Series Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(300)
        self.series_area = QWidget()
        self.series_layout = QVBoxLayout(self.series_area)
        self.series_layout.setContentsMargins(0, 0, 0, 0)
        self.series_layout.addStretch()
        scroll.setWidget(self.series_area)
        config_layout.addWidget(scroll)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # Connect signals
        self.radio_raw.toggled.connect(self.update_series_ui)
        self.radio_mag.toggled.connect(self.update_series_ui)

        # Load Data
        self.load_csv_preview()
        self.update_series_ui()

    def load_csv_preview(self):
        try:
            with open(self.csv_path, 'r', newline='') as f:
                reader = csv.reader(f)
                try:
                    self.headers = next(reader)
                except StopIteration:
                    self.headers = []

                self.preview_data = []
                for i, row in enumerate(reader):
                    if i < 5: self.preview_data.append(row)
                    else: break

            if not self.headers:
                QMessageBox.critical(self, "Error", "CSV file is empty or invalid.")
                self.reject()
                return

            self.table.setColumnCount(len(self.headers))
            self.table.setHorizontalHeaderLabels(self.headers)
            self.table.setRowCount(len(self.preview_data))

            for r, row in enumerate(self.preview_data):
                for c, val in enumerate(row):
                    if c < len(self.headers):
                        self.table.setItem(r, c, QTableWidgetItem(val))

            self.table.resizeColumnsToContents()
            self.populate_combos()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV: {e}")
            self.reject()

    def populate_combos(self):
        self.time_combo.clear()
        self.time_combo.addItems(self.headers)
        # Smart detect Time
        for i, h in enumerate(self.headers):
            lower = h.lower()
            if 'time' in lower or 'ts' == lower or 'timestamp' == lower:
                self.time_combo.setCurrentIndex(i)
                break

    def update_series_ui(self):
        # Clear existing widgets
        while self.series_layout.count() > 1: # Keep stretch item
            item = self.series_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        mode = "raw" if self.radio_raw.isChecked() else "magnitude"
        self.series_widgets = []

        if mode == "raw":
            for i in range(1, 4):
                group = QGroupBox(f"Series {i}")
                layout = QHBoxLayout()
                combo = QComboBox()
                combo.addItem("-- None --", None)
                for h in self.headers: combo.addItem(h, h)

                layout.addWidget(QLabel("Column:"))
                layout.addWidget(combo)
                group.setLayout(layout)

                # Insert before stretch
                self.series_layout.insertWidget(self.series_layout.count()-1, group)
                self.series_widgets.append({'combo': combo})

        else: # Magnitude
            for i in range(1, 4):
                group = QGroupBox(f"Series {i} (Vector)")
                layout = QGridLayout()

                widgets = {}
                for idx, axis in enumerate(['X', 'Y', 'Z']):
                    layout.addWidget(QLabel(f"{axis}:"), idx, 0)
                    combo = QComboBox()
                    combo.addItem("-- None --", None)
                    for h in self.headers: combo.addItem(h, h)
                    layout.addWidget(combo, idx, 1)
                    widgets[axis] = combo

                    # Smart Auto-select
                    hint = ''
                    if i == 1: hint = 'A' # Accel
                    elif i == 2: hint = 'G' # Gyro
                    elif i == 3: hint = 'M' # Mag or Pressure? No, Mag usually M

                    target_start = (hint + axis).lower()
                    if hint:
                        for idx_h, h in enumerate(self.headers):
                            if h.lower().startswith(target_start):
                                combo.setCurrentIndex(idx_h + 1)
                                break

                group.setLayout(layout)
                self.series_layout.insertWidget(self.series_layout.count()-1, group)
                self.series_widgets.append(widgets)

    def validate_and_accept(self):
        time_col = self.time_combo.currentText()
        mode = "raw" if self.radio_raw.isChecked() else "magnitude"
        series_list = []

        valid_series_found = False

        if mode == "raw":
            for idx, w in enumerate(self.series_widgets):
                col = w['combo'].currentData()
                if col:
                    series_list.append({
                        'type': 'raw',
                        'col': col,
                        'label': f"Series {idx+1} ({col})"
                    })
                    valid_series_found = True
        else:
            for idx, w in enumerate(self.series_widgets):
                x = w['X'].currentData()
                y = w['Y'].currentData()
                z = w['Z'].currentData()
                if x and y and z:
                    series_list.append({
                        'type': 'magnitude',
                        'x': x, 'y': y, 'z': z,
                        'label': f"Series {idx+1} Mag"
                    })
                    valid_series_found = True

        if not time_col:
            QMessageBox.warning(self, "Validation Error", "Please select a Time column.")
            return

        if not valid_series_found:
            QMessageBox.warning(self, "Validation Error", "Please select at least one valid data series.")
            return

        self.result_config = {
            'time_col': time_col,
            'mode': mode,
            'series': series_list
        }
        self.accept()

class SyncPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dog Agility Sync Tool")
        self.setStyleSheet(STYLE_SHEET)

        self.cap = None
        self.is_playing = False
        self.video_time_ms = 0
        self.offset_ms = 0
        self.idx = -1
        self.dirs = []
        self.current_video_path = None
        self.computer_name = platform.node()
        self.marks = {k: None for k in ['stride_start', 'obs_start', 'obs_stop', 'stride_stop']}
        self.marker_btns = {}
        self.audio_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.playback_rate = 0.25
        self.is_saved = False

        self.central = QWidget()
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        dir_btn = QPushButton("📂 Open Directory")
        dir_btn.clicked.connect(self.choose_directory)
        dir_btn.setFixedWidth(140)

        self.file_lbl = QLabel("No File Loaded")
        self.file_lbl.setStyleSheet("font-size: 16px; color: #ffffff;")

        self.next_btn = QPushButton("Next File ⏭")
        self.next_btn.clicked.connect(self.next_file)
        self.next_btn.setFixedWidth(120)
        self.next_btn.setEnabled(False)

        toolbar.addWidget(dir_btn)
        toolbar.addWidget(self.file_lbl)
        toolbar.addStretch()
        toolbar.addWidget(self.next_btn)
        layout.addLayout(toolbar)

        # Splitter
        self.splitter = QSplitter(Qt.Vertical)
        self.video_lbl = QLabel()
        self.video_lbl.setStyleSheet("background-color: black;")
        self.video_lbl.setAlignment(Qt.AlignCenter)
        self.video_lbl.setMinimumSize(400, 300)

        self.spectrogram = SpectrogramCanvas(self)
        self.plot = MatplotlibCanvas(self)

        self.splitter.addWidget(self.video_lbl)
        self.splitter.addWidget(self.spectrogram)
        self.splitter.addWidget(self.plot)
        layout.addWidget(self.splitter)

        # Time Scroll
        scroll_layout = QHBoxLayout()
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.sliderMoved.connect(self.scrub_video)
        scroll_layout.addWidget(QLabel("Time:")); scroll_layout.addWidget(self.time_slider)
        layout.addLayout(scroll_layout)

        # Controls
        ctrls = QVBoxLayout()
        ctrls.setSpacing(12)

        # Row 1: Playback & Sync
        row_play = QHBoxLayout()
        self.play_btn = QPushButton("▶ PLAY")
        self.play_btn.setFixedWidth(100)
        self.play_btn.clicked.connect(self.toggle_play)

        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(0, 60000)
        self.offset_slider.setValue(30000)
        self.offset_slider.valueChanged.connect(self.update_offset)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1.0x", "0.5x", "0.25x"])
        self.speed_combo.setCurrentText("0.25x")
        self.speed_combo.currentTextChanged.connect(self.change_speed)
        self.speed_combo.setFixedWidth(70)

        row_play.addWidget(self.play_btn)
        row_play.addWidget(self.speed_combo)
        row_play.addSpacing(20)
        row_play.addWidget(QLabel("Sync Offset:"))
        row_play.addWidget(self.offset_slider)
        ctrls.addLayout(row_play)

        # Row 2: Markers (Grid Layout for better look)
        marker_layout = QHBoxLayout()
        marker_layout.setSpacing(10)

        # Stride Buttons
        self.stride_start_btn = self.create_marker_btn('stride_start', "Stride Start (S)", "#448aff")
        self.stride_stop_btn = self.create_marker_btn('stride_stop', "Stride Stop (F)", "#e040fb")

        # Obstacle Buttons
        self.obs_start_btn = self.create_marker_btn('obs_start', "Obstacle Start (D)", "#69f0ae")
        self.obs_stop_btn = self.create_marker_btn('obs_stop', "Obstacle Stop (G)", "#ff5252")

        marker_layout.addWidget(self.stride_start_btn)
        marker_layout.addWidget(self.obs_start_btn)
        marker_layout.addWidget(self.obs_stop_btn)
        marker_layout.addWidget(self.stride_stop_btn)

        ctrls.addLayout(marker_layout)

        # Row 3: Actions
        row_act = QHBoxLayout()
        clr_btn = QPushButton("🗑 Clear Marks")
        clr_btn.clicked.connect(self.clear_all)
        clr_btn.setStyleSheet("background-color: #5d4037; border-color: #5d4037;")

        self.save_btn = QPushButton("💾 Save Data")
        self.save_btn.clicked.connect(self.save_data)
        self.save_btn.setStyleSheet("background-color: #00bcd4; color: #ffffff; font-weight: bold; font-size: 14px; padding: 8px;")

        self.abnormal_cb = QCheckBox("Abnormal")
        self.abnormal_cb.setStyleSheet("color: #ff5252; font-weight: bold;")

        self.toggle_spec_btn = QPushButton("Toggle Spectrogram")
        self.toggle_spec_btn.clicked.connect(self.toggle_spectrogram)
        self.toggle_spec_btn.setCheckable(True)
        self.toggle_spec_btn.setChecked(True)

        row_act.addStretch()
        row_act.addWidget(self.toggle_spec_btn)
        row_act.addWidget(self.abnormal_cb)
        row_act.addWidget(clr_btn)
        row_act.addWidget(self.save_btn)
        ctrls.addLayout(row_act)

        layout.addLayout(ctrls)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)
        self.audio_player.setPlaybackRate(self.playback_rate)

        # Enforce initial visibility state
        self.toggle_spectrogram()

    def change_speed(self, text):
        rate = float(text.replace('x', ''))
        self.playback_rate = rate
        self.audio_player.setPlaybackRate(rate)

    def create_marker_btn(self, key, text, color_hex):
        btn = QPushButton(text)
        btn.setStyleSheet(f"border-bottom: 3px solid {color_hex}; font-weight: bold;")
        btn.clicked.connect(lambda: self.add_mark(key))
        btn.setToolTip("Select a file to see definition")
        self.marker_btns[key] = btn
        return btn

    def choose_directory(self):
        p = QFileDialog.getExistingDirectory(self, "Select Root")
        if p:
            self.dirs = [os.path.join(p, d) for d in sorted(os.listdir(p)) if os.path.isdir(os.path.join(p, d))]
            if self.dirs:
                self.idx = 0
                self.load_file(0)
                self.next_btn.setEnabled(len(self.dirs) > 1)

    def detect_obstacle_type(self, path):
        path_lower = path.lower()
        if 'jump' in path_lower: return 'jump'
        if 'tunnel' in path_lower: return 'tunnel'
        if 'teeter' in path_lower: return 'teeter'
        if 'aframe' in path_lower or 'a-frame' in path_lower: return 'aframe'
        if 'dogwalk' in path_lower: return 'dogwalk'
        if 'weave' in path_lower: return 'weave'
        return 'flat'

    def update_tooltips(self, obs_type):
        tips = TOOLTIPS.get(obs_type, TOOLTIPS['flat'])
        for key, text in tips.items():
            if key in self.marker_btns:
                self.marker_btns[key].setToolTip(text)

    def load_file(self, i):
        self.clear_all()
        dir_path = self.dirs[i]
        v, c = find_video_csv_pair(dir_path)

        if not v or not c:
            QMessageBox.warning(self, "Error", f"Could not find video/CSV pair in {dir_path}")
            return

        # Update tooltips based on file name/path
        obs_type = self.detect_obstacle_type(dir_path)
        self.update_tooltips(obs_type)

        # --- MODAL INTEGRATION ---
        # We need to ask for column configuration if it's the first file,
        # or perhaps re-use it? For now, let's ask every time or once?
        # The requirement was "persistence: apply to subsequent files".
        if not hasattr(self, 'column_config') or self.column_config is None:
            dlg = ColumnSelectionDialog(c, self)
            if dlg.exec_() == QDialog.Accepted:
                self.column_config = dlg.result_config
            else:
                # User cancelled
                return

        df, err = load_data(c, self.column_config)
        if df is not None:
            self.plot.update_data(df, self.column_config)
            if self.cap: self.cap.release()
            self.cap = cv2.VideoCapture(v)
            self.current_video_path = v
            self.time_slider.setRange(0, int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            self.file_lbl.setText(f"File: {os.path.basename(dir_path)} ({obs_type.upper()})")

            audio_path = ensure_audio_extracted(v)
            if audio_path:
                self.spectrogram.update_data(audio_path)
                url = QUrl.fromLocalFile(os.path.abspath(audio_path))
                self.audio_player.setMedia(QMediaContent(url))
            else:
                self.spectrogram.update_data(None)
                self.audio_player.setMedia(QMediaContent())

            self.video_time_ms = 0
            self.is_playing = False
            self.play_btn.setText("▶ PLAY")
            self.show_frame()
        else:
             QMessageBox.critical(self, "Error", f"Failed to load data: {err}")

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.setText("⏸ PAUSE" if self.is_playing else "▶ PLAY")
        if self.is_playing:
            self.audio_player.play()
        else:
            self.audio_player.pause()

    def toggle_spectrogram(self):
        self.spectrogram.setVisible(self.toggle_spec_btn.isChecked())

    def update_frame(self):
        if self.is_playing and self.cap:
            has_audio = not self.audio_player.media().isNull()
            ret = False
            frame = None

            if has_audio and self.audio_player.state() == QMediaPlayer.PlayingState:
                audio_t = self.audio_player.position()
                self.video_time_ms = audio_t

                # Check drift, but only correct if significant to avoid choppy seek
                cap_t = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                drift = audio_t - cap_t

                # If drift is large (> 400ms), seek. Otherwise just grab next frame.
                if abs(drift) > 400:
                    self.cap.set(cv2.CAP_PROP_POS_MSEC, audio_t)
                elif drift > 50: # If video is behind, read an extra frame to catch up
                     self.cap.read()

                ret, frame = self.cap.read()
            else:
                ret, frame = self.cap.read()
                if ret:
                    self.video_time_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))

            if ret:
                self.time_slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
                self.display_img(frame)
                self.plot.update_cursor(self.video_time_ms, self.offset_ms)
                self.spectrogram.update_cursor(self.video_time_ms)
            else:
                self.is_playing = False
                self.play_btn.setText("▶ PLAY")
                self.audio_player.pause()

    def scrub_video(self, val):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, val)
            ret, frame = self.cap.read()
            if ret:
                self.video_time_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
                self.audio_player.setPosition(self.video_time_ms)
                self.display_img(frame)
                self.plot.update_cursor(self.video_time_ms, self.offset_ms)
                self.spectrogram.update_cursor(self.video_time_ms)

    def show_frame(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, self.video_time_ms)
            ret, frame = self.cap.read()
            if ret:
                self.display_img(frame)
                self.spectrogram.update_cursor(self.video_time_ms)

    def display_img(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
        self.video_lbl.setPixmap(QPixmap.fromImage(qimg).scaled(self.video_lbl.size(), Qt.KeepAspectRatio))

    def update_offset(self, val):
        self.offset_ms = val - 30000; self.plot.update_cursor(self.video_time_ms, self.offset_ms)

    def add_mark(self, key):
        self.marks[key] = self.video_time_ms; self.plot.set_marker(key, self.video_time_ms, self.offset_ms)

    def clear_all(self):
        self.marks = {k: None for k in self.marks.keys()}
        self.abnormal_cb.setChecked(False)
        self.plot.clear_markers()

    def save_data(self):
        if self.idx == -1: return
        log = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Directory': os.path.basename(self.dirs[self.idx]),
            'Offset_ms': self.offset_ms,
            'Abnormal': self.abnormal_cb.isChecked()
        }
        log.update({f"{k}_ms": v for k, v in self.marks.items()})
        fieldnames = log.keys()
        exists = os.path.exists(LOG_FILE)
        try:
            with open(LOG_FILE, 'a', newline='') as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                if not exists: w.writeheader()
                w.writerow(log)
            self.is_saved = True
            self.next_file()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save data: {e}")

    def next_file(self):
        if not self.is_saved:
            QMessageBox.information(self, "Have you saved?", "Use the save button before continuing!")
        elif self.idx < len(self.dirs) - 1:
            self.is_saved = False
            self.idx += 1; self.load_file(self.idx)
        else:
            QMessageBox.information(self, "Done", "All files in directory processed!")

    def keyPressEvent(self, e):
        mapping = {
            Qt.Key_Space: self.toggle_play,
            Qt.Key_S: lambda: self.add_mark('stride_start'),
            Qt.Key_D: lambda: self.add_mark('obs_start'),
            Qt.Key_F: lambda: self.add_mark('obs_stop'),
            Qt.Key_G: lambda: self.add_mark('stride_stop'),
            Qt.Key_Return: self.save_data
        }
        if e.key() in mapping: mapping[e.key()]()
        else: super().keyPressEvent(e)

if __name__ == '__main__':
    app = QApplication(sys.argv); player = SyncPlayer(); player.show(); sys.exit(app.exec_())
