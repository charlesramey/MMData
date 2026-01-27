import pandas as pd
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QMessageBox, QFileDialog, QLineEdit, QSplitter, QCheckBox
)
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer, QSize, QSettings
import sys
import subprocess
import os
import csv
import platform  
import time      
from datetime import datetime
from scipy.signal import butter, filtfilt

# --- CONFIGURATION ---
DOWNSCALED_VIDEO_PREFIX = 'downscaled_720p_v3_'
OFFSET_RANGE_MS = 30000 
VIDEO_SIZE = (620, 440) 

if platform.system() == 'Darwin':  # macOS
    LOG_DIR = os.path.expanduser("~/Documents/DogAgilityLogs")
else: # Windows/Other
    LOG_DIR = os.getcwd()

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'sync_log.csv')
# ---------------------

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

def find_video_csv_pair(directory):
    video_file = None
    csv_file = None
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        if os.path.isfile(full_path):
            if item.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')) and video_file is None:
                video_file = full_path
            elif item.lower().endswith('.csv') and csv_file is None:
                csv_file = full_path
            if video_file and csv_file:
                break
    return video_file, csv_file

def load_data(csv_path):
    try:
        df = pd.read_csv(csv_path)
        if df.empty: return None, "CSV file is empty."
    except Exception as e: return None, f"Error loading CSV: {e}"

    if 'Timestamp' not in df.columns or 'Ax' not in df.columns:
        return None, "Error: 'Timestamp' or 'Ax' column not found in CSV."

    df['Relative_Time_s'] = df['Timestamp'] - df['Timestamp'].iloc[0]
    df['Relative_Time_ms'] = df['Relative_Time_s'] * 1000
    return df, None

def find_closest_data_index(df, target_time_ms):
    time_series = df['Relative_Time_ms'].values
    idx = np.searchsorted(time_series, target_time_ms, side="left")
    if idx == 0: return 0
    if idx == len(df): return len(df) - 1
    return idx if abs(time_series[idx-1] - target_time_ms) > abs(time_series[idx] - target_time_ms) else idx - 1

class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        super().__init__(fig)
        self.setParent(parent)
        self.reset_marker_objects()
        plt.tight_layout(pad=0.25)

    def reset_marker_objects(self):
        self.point_marker, = self.ax.plot([], [], 'o', color='red', markersize=6, zorder=10)
        self.m = {
            'stride_start': (self.ax.axvline(x=np.nan, color='blue', ls='--', alpha=0), self.ax.text(0,0,'',color='blue',fontsize=8,fontweight='bold')),
            'obs_start': (self.ax.axvline(x=np.nan, color='green', ls=':', alpha=0), self.ax.text(0,0,'',color='green',fontsize=8,fontweight='bold')),
            'obs_stop': (self.ax.axvline(x=np.nan, color='red', ls=':', alpha=0), self.ax.text(0,0,'',color='red',fontsize=8,fontweight='bold')),
            'stride_stop': (self.ax.axvline(x=np.nan, color='purple', ls='--', alpha=0), self.ax.text(0,0,'',color='purple',fontsize=8,fontweight='bold'))
        }

    def clear_markers(self):
        for line, label in self.m.values():
            line.set_xdata([np.nan]); line.set_alpha(0); label.set_alpha(0)
        self.point_marker.set_data([], [])
        self.draw()

    def update_data(self, df):
        self.df = df
        a_mag = np.sqrt(df['Ax']**2 + df['Ay']**2 + df['Az']**2)
        g_mag = np.sqrt(df['Gx']**2 + df['Gy']**2 + df['Gz']**2)
        diffs = np.diff(df['Relative_Time_s'])
        fs = 1.0 / np.mean(diffs) if len(diffs) > 0 else 100.0
        self.df['Amag_F'] = apply_lowpass(a_mag, 5.0, fs)
        self.df['Gmag_F'] = apply_lowpass(g_mag, 5.0, fs)
        
        self.df['Amag_F_norm'] = (self.df['Amag_F'] - self.df['Amag_F'].mean())/self.df['Amag_F'].std()
        self.df['Gmag_F_norm'] = (self.df['Gmag_F'] - self.df['Gmag_F'].mean())/self.df['Gmag_F'].std()
        a_mag_norm = (a_mag - np.mean(a_mag)) / np.std(a_mag)
        g_mag_norm = (g_mag - np.mean(g_mag)) / np.std(g_mag)
        
        self.ax.clear()
        self.ax.plot(df['Relative_Time_s'], a_mag_norm, color='lightblue', lw=0.8, alpha=0.6)
        self.ax.plot(df['Relative_Time_s'], self.df['Amag_F_norm'], color='#003366', lw=1.5, label='Accel (5Hz)')
        self.ax.plot(df['Relative_Time_s'], g_mag_norm, color='lightcoral', lw=0.8, alpha=0.6)
        self.ax.plot(df['Relative_Time_s'], self.df['Gmag_F_norm'], color='#663300', lw=1.5, label='Gyro (5Hz)')
        
        if 'Pressure' in df.columns:
            p = apply_lowpass(df['Pressure'].values, 2.0, fs)
            p_s = (p - np.mean(p)) / np.std(p)
            self.ax.plot(df['Relative_Time_s'], p_s, color='orange', lw=1.2, alpha=0.7, label='Pressure')
            
        self.ax.grid(True, ls='--', alpha=0.6)
        self.reset_marker_objects()
        self.ax.legend(fontsize=7, loc='upper left')
        self.draw()

    def set_marker(self, key, time_ms, offset_ms):
        line, label = self.m[key]
        time_s = (time_ms + offset_ms) / 1000.0
        line.set_xdata([time_s]); line.set_alpha(1.0)
        label.set_position((time_s, self.ax.get_ylim()[1])); label.set_text(key.upper().replace('_', ' ')); label.set_alpha(1.0)
        self.draw()

    def update_cursor(self, t_ms, offset_ms):
        if self.df is None: return
        idx = find_closest_data_index(self.df, t_ms + offset_ms)
        self.point_marker.set_data([self.df.loc[idx, 'Relative_Time_s']], [self.df.loc[idx, 'Amag_F_norm']])
        self.draw()

class SyncPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dog Agility Sync Tool")
        self.cap = None
        self.is_playing = False
        self.video_time_ms = 0
        self.offset_ms = 0
        self.idx = -1
        self.dirs = []
        self.current_video_path = None
        self.computer_name = platform.node()
        self.marks = {k: None for k in ['stride_start', 'obs_start', 'obs_stop', 'stride_stop']}
        
        self.central = QWidget()
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)

        # Header
        header = QHBoxLayout()
        self.file_lbl = QLabel("File: None")
        dir_btn = QPushButton("Choose Directory")
        dir_btn.clicked.connect(self.choose_directory)
        self.next_btn = QPushButton("Next File >>")
        self.next_btn.clicked.connect(self.next_file)
        header.addWidget(self.file_lbl); header.addWidget(dir_btn); header.addWidget(self.next_btn)
        layout.addLayout(header)

        # Splitter
        self.splitter = QSplitter(Qt.Vertical)
        self.video_lbl = QLabel(); self.video_lbl.setStyleSheet("background-color: black;"); self.video_lbl.setAlignment(Qt.AlignCenter); self.video_lbl.setMinimumSize(400, 300)
        self.plot = MatplotlibCanvas(self)
        self.splitter.addWidget(self.video_lbl); self.splitter.addWidget(self.plot)
        layout.addWidget(self.splitter)

        # Time Scroll
        scroll_layout = QHBoxLayout()
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.sliderMoved.connect(self.scrub_video)
        scroll_layout.addWidget(QLabel("Time:")); scroll_layout.addWidget(self.time_slider)
        layout.addLayout(scroll_layout)

        # Controls
        ctrls = QVBoxLayout()
        row_play = QHBoxLayout()
        self.play_btn = QPushButton("PLAY")
        self.play_btn.clicked.connect(self.toggle_play)
        self.offset_slider = QSlider(Qt.Horizontal); self.offset_slider.setRange(0, 60000); self.offset_slider.setValue(30000); self.offset_slider.valueChanged.connect(self.update_offset)
        row_play.addWidget(self.play_btn); row_play.addWidget(QLabel("Sync Offset:")); row_play.addWidget(self.offset_slider)
        ctrls.addLayout(row_play)

        # Markers
        row_marks = QHBoxLayout()
        for k in self.marks.keys():
            btn = QPushButton(k.replace('_', ' ').title())
            btn.clicked.connect(lambda ch, key=k: self.add_mark(key))
            row_marks.addWidget(btn)
        ctrls.addLayout(row_marks)

        # Action Buttons
        row_act = QHBoxLayout()
        clr_btn = QPushButton("Clear Marks"); clr_btn.clicked.connect(self.clear_all)
        self.abnormal_checkbox = QCheckBox("Abnormal")
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_data)
        self.save_btn.setStyleSheet("background-color: #00bcd4; color: white; font-weight: bold;")
        
        row_act.addWidget(clr_btn)
        row_act.addWidget(self.abnormal_checkbox)
        row_act.addWidget(self.save_btn)
        ctrls.addLayout(row_act)
        
        layout.addLayout(ctrls)
        self.timer = QTimer(); self.timer.timeout.connect(self.update_frame); self.timer.start(33)

    def choose_directory(self):
        p = QFileDialog.getExistingDirectory(self, "Select Root")
        if p:
            self.dirs = [os.path.join(p, d) for d in sorted(os.listdir(p)) if os.path.isdir(os.path.join(p, d))]
            if self.dirs:
                self.idx = 0; self.load_file(0)

    def load_file(self, i):
        self.clear_all()
        dir_path = self.dirs[i]
        v, c = find_video_csv_pair(dir_path)
        df, _ = load_data(c)
        if df is not None:
            self.plot.update_data(df)
            if self.cap: self.cap.release()
            self.cap = cv2.VideoCapture(v)
            self.current_video_path = v
            self.time_slider.setRange(0, int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            self.file_lbl.setText(f"File: {os.path.basename(dir_path)}")
            self.video_time_ms = 0; self.is_playing = False; self.play_btn.setText("PLAY")
            self.abnormal_checkbox.setChecked(False) 
            self.show_frame()

    def toggle_play(self):
        self.is_playing = not self.is_playing; self.play_btn.setText("PAUSE" if self.is_playing else "PLAY")

    def update_frame(self):
        if self.is_playing and self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.video_time_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
                self.time_slider.setValue(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
                self.display_img(frame)
                self.plot.update_cursor(self.video_time_ms, self.offset_ms)
            else: self.is_playing = False; self.play_btn.setText("PLAY")

    def scrub_video(self, val):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, val)
            ret, frame = self.cap.read()
            if ret:
                self.video_time_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
                self.display_img(frame)
                self.plot.update_cursor(self.video_time_ms, self.offset_ms)

    def show_frame(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, self.video_time_ms)
            ret, frame = self.cap.read()
            if ret: self.display_img(frame)

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
        self.marks = {k: None for k in self.marks.keys()}; self.plot.clear_markers()

    def save_data(self):
        if self.idx == -1: return
        
        fieldnames = [
            'Timestamp', 'Computer_Name', 'Directory', 'Video_File', 'Offset_ms', 'Abnormal',
            'stride_start_ms', 'obs_start_ms', 'obs_stop_ms', 'stride_stop_ms'
        ]
        
        log = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            'Computer_Name': self.computer_name,
            'Directory': os.path.basename(self.dirs[self.idx]), 
            'Video_File': os.path.basename(self.current_video_path) if self.current_video_path else 'N/A',
            'Offset_ms': self.offset_ms,
            'Abnormal': 1 if self.abnormal_checkbox.isChecked() else 0
        }
        log.update({f"{k}_ms": v for k, v in self.marks.items()})
        
        exists = os.path.exists(LOG_FILE)
        try:
            with open(LOG_FILE, 'a', newline='') as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                if not exists: w.writeheader()
                w.writerow(log)
            self.next_file()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save data: {e}")

    def next_file(self):
        if self.idx < len(self.dirs) - 1:
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