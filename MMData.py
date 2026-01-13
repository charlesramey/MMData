import pandas as pd
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QMessageBox, QFileDialog, QLineEdit, QSplitter
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, QSize, QSettings
import sys
import subprocess
import os
import csv
from datetime import datetime
from scipy.signal import butter, filtfilt

# --- CONFIGURATION ---
DOWNSCALED_VIDEO_PREFIX = 'downscaled_720p_v3_'
OFFSET_RANGE_MS = 30000 
VIDEO_SIZE = (620, 440) 
# ---------------------

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def apply_lowpass(data, cutoff, fs, order=4):
    """Applies a Zero-phase Butterworth Low-Pass Filter."""
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

def run_ffmpeg_downscale(input_file, video_output_file):
    if not os.path.exists(input_file):
        return None, "Original video file not found."
    original_filename = os.path.basename(input_file)
    if '720' in original_filename.lower():
        return input_file, None

    if not os.path.exists(video_output_file):
        ffmpeg_exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg' 
        ffmpeg_path = get_resource_path(ffmpeg_exe)
        video_command = [
            ffmpeg_path, '-i', input_file, '-vf', 'scale=1280:-2', 
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast', '-an', '-y', video_output_file
        ]
        try:
            subprocess.run(video_command, check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            video_output_file = input_file 
            
    return video_output_file, None

def load_data(csv_path):
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            return None, "CSV file is empty."
    except Exception as e:
        return None, f"Error loading CSV: {e}"

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
    if abs(time_series[idx-1] - target_time_ms) < abs(time_series[idx] - target_time_ms):
        return idx - 1
    else:
        return idx

class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        super().__init__(fig)
        self.setParent(parent)
        self.setMinimumHeight(100)
        self.df = None
        
        self.point_marker, = self.ax.plot([], [], 'o', color='red', markersize=6, label='Current Point')
        self.start_line = self.ax.axvline(x=0, color='green', linestyle='--', alpha=0)
        self.start_label = self.ax.text(0, 0, '', color='green', fontweight='bold', verticalalignment='bottom', fontsize=8)
        self.stop_line = self.ax.axvline(x=0, color='red', linestyle='--', alpha=0)
        self.stop_label = self.ax.text(0, 0, '', color='red', fontweight='bold', verticalalignment='bottom', fontsize=8)
        
        self.ax.legend(fontsize=7, loc='upper left')
        plt.tight_layout(pad=0.25)

    def clear_plot(self):
        self.df = None
        self.ax.clear()
        self.ax.set_title('No Data Loaded', fontsize=10)
        self.draw()

    def update_data(self, df):
        self.df = df
        accel_mag = np.sqrt(df['Ax']**2 + df['Ay']**2 + df['Az']**2)
        self.df['Amag'] = accel_mag

        time_diffs = np.diff(df['Relative_Time_s'])
        fs = 1.0 / np.mean(time_diffs) if len(time_diffs) > 0 else 100.0
        self.df['Amag_Filtered'] = apply_lowpass(accel_mag, cutoff=5.0, fs=fs)

        self.ax.clear()
        self.ax.plot(self.df['Relative_Time_s'], self.df['Amag'], 
                     label='Accel Raw', color='lightblue', linewidth=0.8, alpha=0.6)
        self.ax.plot(self.df['Relative_Time_s'], self.df['Amag_Filtered'], 
                     label='Accel Filtered (5Hz)', color='#003366', linewidth=1.5)
        
        if {'Gx', 'Gy', 'Gz'}.issubset(df.columns):
            gyro_mag = np.sqrt(df['Gx']**2 + df['Gy']**2 + df['Gz']**2)
            scale_factor = accel_mag.max() / gyro_mag.max() if gyro_mag.max() > 0 else 1.0
            self.df['Gmag_scaled'] = gyro_mag * scale_factor
            self.ax.plot(self.df['Relative_Time_s'], self.df['Gmag_scaled'], label=f"Gyro (scaled x{scale_factor:.1f})", color='green', linewidth=1.0, alpha=0.6)

        self.ax.tick_params(axis='both', which='major', labelsize=7)
        self.ax.grid(True, linestyle='--', alpha=0.6)
        
        self.point_marker, = self.ax.plot([], [], 'o', color='red', markersize=6, label='Sync Point')
        self.start_line = self.ax.axvline(x=0, color='green', linestyle='--', alpha=0)
        self.start_label = self.ax.text(0, 0, '', color='green', fontweight='bold', verticalalignment='bottom', fontsize=8)
        self.stop_line = self.ax.axvline(x=0, color='red', linestyle='--', alpha=0)
        self.stop_label = self.ax.text(0, 0, '', color='red', fontweight='bold', verticalalignment='bottom', fontsize=8)
        
        self.ax.legend(fontsize=7, loc='upper left')
        plt.tight_layout(pad=0.5)

    def set_start_marker(self, time_s):
        self.start_line.set_xdata([time_s])
        self.start_line.set_alpha(1.0)
        y_max = self.ax.get_ylim()[1]
        self.start_label.set_position((time_s, y_max))
        self.start_label.set_text('START')
        self.start_label.set_alpha(1.0)
        self.draw()

    def set_stop_marker(self, time_s):
        self.stop_line.set_xdata([time_s])
        self.stop_line.set_alpha(1.0)
        y_max = self.ax.get_ylim()[1]
        self.stop_label.set_position((time_s, y_max))
        self.stop_label.set_text('STOP')
        self.stop_label.set_alpha(1.0)
        self.draw()

    def update_marker(self, target_data_time_ms, sync_offset_ms, is_playing):
        if self.df is None or self.df.empty:
            return
            
        min_dt, max_dt = self.df['Relative_Time_ms'].min(), self.df['Relative_Time_ms'].max()
        if min_dt <= target_data_time_ms <= max_dt:
            idx = find_closest_data_index(self.df, target_data_time_ms)
            self.point_marker.set_data([self.df.loc[idx, 'Relative_Time_s']], [self.df.loc[idx, 'Amag_Filtered']])
        else:
            self.point_marker.set_data([], [])

        status = "PLAYING" if is_playing else "PAUSED"
        self.ax.set_title(f'Status: {status} | Sync Offset: {sync_offset_ms/1000.0:.3f} s', fontsize=10)
        self.draw()

class VideoFrameWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(320, 240))
        self.setStyleSheet("background-color: black;") 

class SyncPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video & Data Synchronizer")
        # Identifiers for persistent settings
        self.settings = QSettings("GeorgiaTech", "DogAgilitySyncTool")

        self.offset_ms = 0
        self.video_time_ms = 0
        self.is_playing = False
        self.df = None
        self.cap = None
        self.video_duration = 0
        self.fps = 0
        self.frame_delay = 33

        self.root_dir = None
        self.file_dirs = []
        self.current_dir_index = -1
        self.current_video_path = None
        self.current_csv_path = None
        self.obstacle_start_time = None 
        self.obstacle_stop_time = None 
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self._setup_ui()
        self.load_ui_settings()
        
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.update_frame)
        self.playback_timer.start(self.frame_delay)
        
    def _setup_ui(self):
        header = QHBoxLayout()
        self.file_label = QLabel("Current File: None")
        self.choose_btn = QPushButton("Choose Directory")
        self.choose_btn.clicked.connect(self.choose_directory)
        self.next_btn = QPushButton("Next File >>")
        self.next_btn.clicked.connect(self.next_file)
        header.addWidget(self.file_label)
        header.addWidget(self.choose_btn)
        header.addWidget(self.next_btn)
        self.main_layout.addLayout(header)

        self.splitter = QSplitter(Qt.Vertical)
        
        self.video_frame_widget = VideoFrameWidget(self)
        self.splitter.addWidget(self.video_frame_widget)

        self.plot_container = QWidget()
        plot_layout = QVBoxLayout(self.plot_container)
        plot_layout.setContentsMargins(0,0,0,0)
        self.plot_canvas = MatplotlibCanvas(self)
        self.plot_toolbar = NavigationToolbar(self.plot_canvas, self)
        plot_layout.addWidget(self.plot_toolbar)
        plot_layout.addWidget(self.plot_canvas)
        self.splitter.addWidget(self.plot_container)

        self.controls_container = QWidget()
        ctrl_layout = QVBoxLayout(self.controls_container)
        
        play_row = QHBoxLayout()
        self.play_btn = QPushButton("PLAY")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(0, OFFSET_RANGE_MS * 2)
        self.offset_slider.setValue(OFFSET_RANGE_MS)
        self.offset_slider.valueChanged.connect(self.update_offset_value)
        self.pos_slider = QSlider(Qt.Horizontal)
        self.pos_slider.sliderMoved.connect(self.update_scrub_position)
        play_row.addWidget(self.play_btn)
        play_row.addWidget(QLabel("Offset:"))
        play_row.addWidget(self.offset_slider)
        play_row.addWidget(QLabel("Time:"))
        play_row.addWidget(self.pos_slider)
        ctrl_layout.addLayout(play_row)

        anno_row = QHBoxLayout()
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes on this repetition")
        self.incomplete_btn = QPushButton("Incomplete")
        self.incomplete_btn.setCheckable(True)
        self.missed_btn = QPushButton("Missed Contact")
        self.missed_btn.setCheckable(True)
        anno_row.addWidget(QLabel("Notes:"))
        anno_row.addWidget(self.notes_input)
        anno_row.addWidget(self.incomplete_btn)
        anno_row.addWidget(self.missed_btn)
        ctrl_layout.addLayout(anno_row)

        mark_row = QHBoxLayout()
        self.start_btn = QPushButton("Mark Start")
        self.start_btn.clicked.connect(self.mark_obstacle_start)
        self.stop_btn = QPushButton("Mark Stop")
        self.stop_btn.clicked.connect(self.mark_obstacle_stop)
        self.save_btn = QPushButton("SAVE")
        self.save_btn.clicked.connect(self.save_result)
        self.save_btn.setStyleSheet("background-color: #00bcd4; color: white;")
        mark_row.addWidget(self.start_btn)
        mark_row.addWidget(self.stop_btn)
        mark_row.addWidget(self.save_btn)
        ctrl_layout.addLayout(mark_row)

        self.splitter.addWidget(self.controls_container)
        self.main_layout.addWidget(self.splitter)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; height: 8px; }")
        
        self._set_controls_enabled(False)

    def save_ui_settings(self):
        self.settings.setValue("splitterSizes", self.splitter.saveState())
        self.settings.setValue("windowGeometry", self.saveGeometry())

    def load_ui_settings(self):
        if self.settings.value("splitterSizes"):
            self.splitter.restoreState(self.settings.value("splitterSizes"))
        if self.settings.value("windowGeometry"):
            self.restoreGeometry(self.settings.value("windowGeometry"))

    def closeEvent(self, event):
        self.save_ui_settings()
        if self.cap: self.cap.release()
        super().closeEvent(event)

    def _set_controls_enabled(self, enabled):
        widgets = [self.play_btn, self.offset_slider, self.pos_slider, 
                   self.save_btn, self.start_btn, self.stop_btn, 
                   self.notes_input, self.incomplete_btn, self.missed_btn]
        for w in widgets: w.setEnabled(enabled)

    def choose_directory(self):
        # Using native directory picker - can sometimes lag on macOS due to permissions
        p = QFileDialog.getExistingDirectory(self, "Select Root Directory", os.path.expanduser("~"))
        if p:
            self.root_dir = p
            # Filter for task subdirectories
            self.file_dirs = [
                os.path.join(p, d) for d in sorted(os.listdir(p)) 
                if os.path.isdir(os.path.join(p, d)) and not d.startswith('.')
            ]
            if self.file_dirs:
                self.current_dir_index = 0
                self.load_file_pair(0)
            else:
                QMessageBox.warning(self, "No Directories", "No task subdirectories found in selected root.")

    def load_file_pair(self, index):
        self.save_ui_settings()
        current_dir = self.file_dirs[index]
        self.file_label.setText(f"File: {os.path.basename(current_dir)}")
        
        video_path, csv_path = find_video_csv_pair(current_dir)
        df, error = load_data(csv_path)
        
        # FIX: Explicit check for None to avoid Ambiguous DataFrame ValueError
        if df is None:
            QMessageBox.critical(self, "Data Error", f"Failed to load CSV: {error}")
            return

        self.df = df
        self.current_video_path, self.current_csv_path = video_path, csv_path
        self.plot_canvas.update_data(self.df)
        
        out_v = os.path.join(current_dir, DOWNSCALED_VIDEO_PREFIX + os.path.basename(video_path))
        v_to_use, _ = run_ffmpeg_downscale(video_path, out_v)
        
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(v_to_use)
        
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Video Error", "Could not open video file.")
            return

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_duration = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) * 1000 / self.fps)
        self.frame_delay = int(1000/self.fps) if self.fps > 0 else 33
        
        # Reset state for new repetition
        self.video_time_ms = 0
        self.offset_ms = 0
        self.obstacle_start_time = None
        self.obstacle_stop_time = None
        self.notes_input.clear()
        self.incomplete_btn.setChecked(False)
        self.missed_btn.setChecked(False)
        self.pos_slider.setRange(0, self.video_duration)
        self._set_controls_enabled(True)
        self.update_frame()

    def update_frame(self):
        if self.is_playing and self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.video_time_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
                self.display_frame(frame)
            else:
                self.is_playing = False
                self.play_btn.setText("PLAY")
                
        self.plot_canvas.update_marker(self.video_time_ms + self.offset_ms, self.offset_ms, self.is_playing)
        if not self.pos_slider.isSliderDown(): 
            self.pos_slider.setValue(self.video_time_ms)

    def display_frame(self, frame):
        if frame is None: return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
        self.video_frame_widget.setPixmap(QPixmap.fromImage(qimg).scaled(self.video_frame_widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mark_obstacle_start(self):
        self.obstacle_start_time = self.video_time_ms
        data_time_s = (self.obstacle_start_time + self.offset_ms) / 1000.0
        self.plot_canvas.set_start_marker(data_time_s)

    def mark_obstacle_stop(self):
        self.obstacle_stop_time = self.video_time_ms
        data_time_s = (self.obstacle_stop_time + self.offset_ms) / 1000.0
        self.plot_canvas.set_stop_marker(data_time_s)

    def next_file(self):
        if self.current_dir_index < len(self.file_dirs) - 1:
            self.current_dir_index += 1
            self.load_file_pair(self.current_dir_index)
        else:
            QMessageBox.information(self, "Done", "All repetitions in this batch are complete!")

    def toggle_playback(self):
        self.is_playing = not self.is_playing
        self.play_btn.setText("PAUSE" if self.is_playing else "PLAY")

    def update_offset_value(self, val):
        self.offset_ms = val - OFFSET_RANGE_MS
        # Re-draw markers with new offset if they've been set
        if self.obstacle_start_time is not None:
            self.plot_canvas.set_start_marker((self.obstacle_start_time + self.offset_ms) / 1000.0)
        if self.obstacle_stop_time is not None:
            self.plot_canvas.set_stop_marker((self.obstacle_stop_time + self.offset_ms) / 1000.0)

    def update_scrub_position(self, pos):
        self.video_time_ms = pos
        self.cap.set(cv2.CAP_PROP_POS_MSEC, pos)
        ret, frame = self.cap.read()
        if ret: self.display_frame(frame)

    def save_result(self):
        log_file = 'sync_log.csv'
        fieldnames = ['Timestamp', 'Directory', 'Video_File', 'CSV_File', 'Offset_ms', 'Start_ms', 'Stop_ms', 'Incomplete', 'Missed_Contact', 'Notes']
        log_data = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Directory': os.path.basename(self.file_dirs[self.current_dir_index]),
            'Video_File': os.path.basename(self.current_video_path),
            'CSV_File': os.path.basename(self.current_csv_path),
            'Offset_ms': self.offset_ms,
            'Start_ms': self.obstacle_start_time if self.obstacle_start_time is not None else 'N/A',
            'Stop_ms': self.obstacle_stop_time if self.obstacle_stop_time is not None else 'N/A',
            'Incomplete': self.incomplete_btn.isChecked(),
            'Missed_Contact': self.missed_btn.isChecked(),
            'Notes': self.notes_input.text()
        }
        exists = os.path.exists(log_file)
        try:
            with open(log_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not exists: writer.writeheader()
                writer.writerow(log_data)
            QMessageBox.information(self, "Saved", f"Results for {log_data['Directory']} logged successfully.")
            self.next_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not log result: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = SyncPlayer()
    player.show()
    sys.exit(app.exec_())