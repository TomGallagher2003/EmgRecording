# movement_timer.py
# PyQt5 app: device select -> device check/init -> random movement -> 4s arc timer -> attempt_classification()
# - Device check/init happens right after selection (session kept open)
# - 4s recording runs in background
# - After recording, classification runs in background; buttons stay disabled and status shows progress messages

import os
import sys
import random

import numpy as np
import requests
from PyQt5 import QtCore, QtGui, QtWidgets

from util.images import Images
from recording import EmgSession  # adjust import path if needed

API_URL = "https://tomsapi.hopto.org"

# Expecting util.images to expose MOVEMENT_TUPLES = list[(clean_name, filename)]
MOVEMENTS = Images.MOVEMENT_TUPLES

# Faster than CSV if you want speedier saves inside attempt_classification
SAVE_AS_NPY = False


class ArcTimerWidget(QtWidgets.QWidget):
    finished = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._duration_ms = 4000
        self._tick_ms = 30
        self._elapsed = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self.setMinimumSize(160, 160)

    def start(self, duration_ms=4000):
        self._duration_ms = max(1, int(duration_ms))
        self._elapsed = 0
        self._progress = 0.0
        self._timer.start(self._tick_ms)
        self.update()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()
        self._progress, self._elapsed = 0.0, 0
        self.update()

    def is_running(self):
        return self._timer.isActive()

    def _on_tick(self):
        self._elapsed += self._tick_ms
        self._progress = min(1.0, self._elapsed / self._duration_ms)
        self.update()
        if self._progress >= 1.0:
            self._timer.stop()
            self.finished.emit()

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        rect = QtCore.QRect(
            (self.width() - side) // 2,
            (self.height() - side) // 2,
            side,
            side,
        )
        start_angle = 90 * 16
        span_angle = -int(self._progress * 360 * 16)

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # background circle
        bg_pen = QtGui.QPen(QtGui.QColor(220, 220, 220), 12)
        p.setPen(bg_pen)
        p.drawEllipse(rect.adjusted(10, 10, -10, -10))

        # foreground arc
        fg_pen = QtGui.QPen(QtGui.QColor(70, 120, 255), 12, cap=QtCore.Qt.RoundCap)
        p.setPen(fg_pen)
        p.drawArc(rect.adjusted(10, 10, -10, -10), start_angle, span_angle)

        # countdown text
        remaining_ms = max(0, self._duration_ms - self._elapsed)
        secs = remaining_ms / 1000.0
        p.setPen(QtGui.QColor(50, 50, 50))
        font = p.font()
        font.setPointSize(int(side * 0.12))
        p.setFont(font)
        p.drawText(rect, QtCore.Qt.AlignCenter, f"{secs:0.1f}s")


class DeviceSelectPage(QtWidgets.QWidget):
    proceed = QtCore.pyqtSignal(bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        title = QtWidgets.QLabel("Select Devices")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        self.cb_emg = QtWidgets.QCheckBox("Use EMG (Muovi)")
        self.cb_emg.setChecked(True)
        self.cb_eeg = QtWidgets.QCheckBox("Use EEG (Muovi+)")
        self.cb_eeg.setChecked(True)

        btn_continue = QtWidgets.QPushButton("Continue")
        btn_continue.setFixedHeight(36)
        btn_continue.clicked.connect(self._on_continue)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addSpacing(16)
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.cb_emg)
        layout.addWidget(self.cb_eeg)
        layout.addStretch(1)
        layout.addWidget(btn_continue)

    def _on_continue(self):
        self.proceed.emit(self.cb_emg.isChecked(), self.cb_eeg.isChecked())


class DeviceInitWorker(QtCore.QThread):
    """Create EmgSession, warm-up/flush, probe capture; emit ready(session) or failed(msg)."""
    ready = QtCore.pyqtSignal(object)   # EmgSession
    failed = QtCore.pyqtSignal(str)

    def __init__(self, use_emg: bool, use_eeg: bool, parent=None):
        super().__init__(parent)
        self.use_emg = use_emg
        self.use_eeg = use_eeg

    def run(self):
        try:
            session = EmgSession(self.use_emg, self.use_eeg)  # sends config on init
            try:
                session.receive_and_ignore(0.75, no_print=True)
                _ = session.get_record(rec_time=0.4)
            except Exception:
                self.failed.emit("Device check failed. Please reboot devices and try again.")
                return

            # ---- API health check ----
            try:
                resp = requests.get(API_URL + "/health", timeout=5)
                print("response: ", resp.text)
                if resp.status_code != 200 or "running" not in resp.text.lower():
                    self.failed.emit(f"API health check failed: {resp.text}")
                    return
            except Exception as e:
                self.failed.emit(f"API unreachable: {e}")
                return

            # If both succeed, continue
            self.ready.emit(session)

        except Exception:
            self.failed.emit("Device init failed. Please reboot devices and try again.")




class RecordingWorker(QtCore.QThread):
    finished_ok = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    capture_started = QtCore.pyqtSignal()  # NEW

    def __init__(self, session: EmgSession, parent=None):
        super().__init__(parent)
        self.session = session

    def run(self):
        try:
            self.capture_started.emit()              # NEW: notify right before capture
            data = self.session.get_record(rec_time=4.0)
            if data is None or data.size == 0:
                self.failed.emit("Recording returned no data.")
                return
            self.finished_ok.emit(data)
        except Exception as e:
            self.failed.emit(str(e))


class ClassificationWorker(QtCore.QThread):
    finished_ok = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(str)

    def __init__(self, classify_fn, movement_name, data, parent=None):
        super().__init__(parent)
        self.classify_fn = classify_fn
        self.movement_name = movement_name
        self.data = data

    def run(self):
        try:
            self.classify_fn(self.movement_name, self.data)
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(str(e))


class ExperimentPage(QtWidgets.QWidget):
    """Random movement + Start (4s) — session is initialized on entry (device check happens here)."""
    def __init__(self, use_emg, use_eeg, parent=None):
        super().__init__(parent)
        self.use_emg = use_emg
        self.use_eeg = use_eeg
        self.current_movement = None
        self.session: EmgSession | None = None
        self.recording_worker = None
        self.is_classifying = False
        self.recording_done = False  # track when recording thread is actually done

        # UI
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumHeight(220)
        self.image_label.setStyleSheet("background: #fafafa; border: 1px solid #e6e6e6;")

        self.name_label = QtWidgets.QLabel("No movement selected")
        self.name_label.setAlignment(QtCore.Qt.AlignCenter)
        self.name_label.setStyleSheet("font-size: 18px;")

        self.status_label = QtWidgets.QLabel("Initializing devices…")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#666;")

        self.btn_random = QtWidgets.QPushButton("Get Random Movement")
        self.btn_random.clicked.connect(self.pick_random_movement)
        self.btn_random.setEnabled(False)  # disabled until devices ready

        self.btn_start = QtWidgets.QPushButton("Start Recording (4s)")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_recording)

        self.arc = ArcTimerWidget()
        self.arc.finished.connect(self._on_arc_complete)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addSpacing(8)
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.btn_random)
        row.addWidget(self.btn_start)
        layout.addLayout(row)
        layout.addWidget(self.arc, 1)
        layout.addStretch(1)

        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Kick off device init immediately
        self._init_worker = DeviceInitWorker(self.use_emg, self.use_eeg, parent=self)
        self._init_worker.ready.connect(self._on_devices_ready)
        self._init_worker.failed.connect(self._on_devices_failed)
        self._init_worker.start()

    # ----- Device init callbacks -----
    def _on_devices_ready(self, session: EmgSession):
        self.session = session
        self.status_label.setText("Devices ready.")
        self.btn_random.setEnabled(True)
        self.btn_start.setEnabled(self.current_movement is not None)

    def _on_devices_failed(self, msg: str):
        self.status_label.setText(msg)

    # ----- Experiment flow -----
    def pick_random_movement(self):
        self.current_movement = random.choice(MOVEMENTS)
        name, filename = self.current_movement
        self.name_label.setText(name)
        img_path = os.path.join(self.script_dir, filename)
        if os.path.exists(img_path):
            pix = QtGui.QPixmap(img_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    self.image_label.size() * 0.95,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled)
            else:
                self.image_label.clear()
        else:
            self.image_label.clear()

        # Enable start if devices ready
        if self.session is not None:
            self.btn_start.setEnabled(True)

    def start_recording(self):
        if self.arc.is_running() or self.session is None:
            return
        if not self.current_movement:
            QtWidgets.QMessageBox.information(self, "Pick a movement", "Please choose a movement first.")
            return

        self.status_label.setText("Recording…")
        self.btn_random.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.recording_done = False

        self.recording_worker = RecordingWorker(self.session, parent=self)
        self.recording_worker.capture_started.connect(lambda: self.arc.start(4000))  # start arc on actual capture start
        self.recording_worker.finished_ok.connect(self._on_recording_finished)
        self.recording_worker.failed.connect(self._on_recording_failed)
        self.recording_worker.start()

    def _on_recording_failed(self, msg: str):
        self.status_label.setText(f"Error: {msg}")
        self.btn_random.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.arc.stop()
        self.recording_done = True

    def _on_recording_finished(self, data):
        self.recording_done = True
        # Start classification immediately when data arrives (buttons remain disabled)
        movement_name = self.current_movement[0] if self.current_movement else None

        self.is_classifying = True
        self.btn_random.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.status_label.setText("Classifying data...")

        self._clf_worker = ClassificationWorker(self.attempt_classification, movement_name, data, parent=self)
        self._clf_worker.finished_ok.connect(self._on_classification_done)
        self._clf_worker.failed.connect(self._on_classification_failed)
        self._clf_worker.start()

    def _on_arc_complete(self):
        # If recording is still finishing behind the scenes, make it explicit to the user.
        if not self.recording_done:
            self.status_label.setText("Finishing capture…")
            # Keep buttons disabled until recording_done and classification both finish.
            return

        # If recording finished but we are still classifying, keep disabled
        if self.is_classifying:
            # Status already says "Classifying data..."
            return

        # Otherwise, re-enable controls (e.g., if something finished very fast)
        self.btn_random.setEnabled(True)
        self.btn_start.setEnabled(self.session is not None and self.current_movement is not None)
        if self.status_label.text().startswith("Recording…"):
            self.status_label.setText("Recording complete.")

    def _on_classification_done(self):
        self.is_classifying = False
        self.status_label.setText("Classification complete.")
        self.btn_random.setEnabled(True)
        self.btn_start.setEnabled(self.session is not None and self.current_movement is not None)

    def _on_classification_failed(self, msg: str):
        self.is_classifying = False
        self.status_label.setText(f"Classification error: {msg}")
        self.btn_random.setEnabled(True)
        self.btn_start.setEnabled(self.session is not None and self.current_movement is not None)

    # ---- Your hook to implement ----
    def attempt_classification(self, movement_name: str, data):
        # Keep your prints so you can see what's happening
        print(f"[attempt_classification] movement: {movement_name}")
        print(f"[attempt_classification] data shape: {getattr(data, 'shape', None)}")

        # Save for inspection (CSV default; toggle to NPY for speed)
        if SAVE_AS_NPY:
            np.save("online_data.npy", data)
            print("[attempt_classification] Saved trial to online_data.npy")
        else:
            if self.session.config.USE_EMG:
                np.savetxt("emg_online_data.csv", data[self.session.config.MUOVI_EMG_CHANNELS].transpose(), delimiter=",")
            if self.session.config.USE_EEG:
                np.savetxt("eeg_online_data.csv", data[self.session.config.MUOVI_PLUES_EEG_CHANNELS].transpose(), delimiter=",")
            print("[attempt_classification] Saved trial ")

        # ---- Sliding window detection -> 1s label mask ----
        fs = int(getattr(self.session.config, "SAMPLE_FREQUENCY", 500))  # samples/sec
        win = 500                      # window size in samples
        hop = 250                      # 50% overlap
        n_samples = data.shape[1]
        labels = np.zeros(n_samples, dtype=np.int32)

        trigger_fn = getattr(self, "window_trigger", None)
        if trigger_fn is None:
            print("[attempt_classification] WARNING: window_trigger(...) not defined; skipping detection.")
        else:
            detected_at = None
            for start in range(0, max(0, n_samples - win + 1), hop):
                window = data[:, start:start + win]   # shape: (channels, win)
                try:
                    if bool(trigger_fn(window)):
                        detected_at = start
                        break
                except Exception as e:
                    print(f"[attempt_classification] window_trigger error at start={start}: {e}")
                    # continue scanning other windows

            if detected_at is not None:
                one_sec = fs
                end = min(n_samples, detected_at + one_sec)
                labels[detected_at:end] = 1
                print(f"[attempt_classification] detected@sample {detected_at} (t={detected_at/fs:.3f}s); "
                      f"marked {end - detected_at} samples (~1s).")
            else:
                print("[attempt_classification] no window detected; labels all zeros.")

        np.savetxt("online_label.csv", labels, fmt="%d", delimiter=",")
        print("[attempt_classification] Saved label file to online_label.csv")

        print("[attempt_classification] classification routine completed")

    def window_trigger(self, window: np.ndarray) -> bool:
        resp = requests.get(API_URL + "/randomClassify", timeout=5)
        return resp.json() in range(10)
    def closeEvent(self, event):
        try:
            if self.session is not None:
                self.session.finish()
        except Exception:
            pass
        super().closeEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Movement Timer & Classifier")
        self.resize(900, 640)
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)
        self.page_select = DeviceSelectPage()
        self.page_select.proceed.connect(self._go_next)
        self.stack.addWidget(self.page_select)

    def _go_next(self, use_emg, use_eeg):
        self.page_experiment = ExperimentPage(use_emg, use_eeg)
        self.stack.addWidget(self.page_experiment)
        self.stack.setCurrentWidget(self.page_experiment)

    def closeEvent(self, event):
        try:
            if hasattr(self, "page_experiment") and self.page_experiment.session is not None:
                self.page_experiment.session.finish()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
