"""
PyQt5-based practice movement viewer.

This module provides two main classes:

- RadialProgress: A custom QWidget that draws a circular countdown indicator,
  useful for visualizing remaining time in a phase. Supports dynamic color.
- GifExerciseViewer: A GUI for guiding practice of EMG/EEG movements using GIFs
  and rest images. Handles sequencing, pre-movement rest, inter-rep rest, repeats,
  a preview image (with red border during pre-movement rest), and a radial timer.

Behavior aligned with the "real" timer UI:
- Pre-movement rest:
    * First movement: fixed 5s (UI only).
    * Between movements: equals inter-rep rest duration (UI only).
    * Preview gets a red border during pre-movement rest.
- Movement:
    * Movement duration shows a green arc.
- Inter-rep rest:
    * Shown only between reps; skipped after the last rep of a movement.
- Time label shows the total phase time for the entire phase (no countdown ticking).
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QTimer, QRectF

from util.images import Images


class RadialProgress(QWidget):
    """Circular progress indicator for countdowns with dynamic color."""

    def __init__(self, diameter=100, thickness=8, parent=None):
        """
        Args:
            diameter (int): Outer diameter of the circle in pixels.
            thickness (int): Thickness of the arc in pixels.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.diameter = diameter
        self.thickness = thickness
        self.setFixedSize(diameter, diameter)
        self._total_ms = 1
        self._remaining_ms = 1
        self._arc_color = QColor("#525c63")  # default; will be set per phase

    def set_color(self, qcolor: QColor):
        """Set the arc color for the next/ongoing phase."""
        self._arc_color = qcolor
        self.update()

    def start(self, total_ms: int):
        """Start a new countdown with a given duration."""
        self._total_ms = max(1, int(total_ms))
        self._remaining_ms = self._total_ms
        self.update()

    def update_value(self, remaining_ms: int):
        """Update the remaining milliseconds for the arc display."""
        self._remaining_ms = max(0, int(remaining_ms))
        self.update()

    def paintEvent(self, event):
        """Custom paint event to draw the background circle and progress arc."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(
            self.thickness / 2,
            self.thickness / 2,
            self.diameter - self.thickness,
            self.diameter - self.thickness,
        )
        # Base circle
        pen = QPen(QColor("#ddd"), self.thickness)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        # Progress arc
        if self._total_ms > 0:
            frac = max(0.0, min(1.0, self._remaining_ms / self._total_ms))
            span = int(360 * frac * 16)
            pen.setColor(self._arc_color)
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -span)


# Movement GIFs (change these to actual paths to your .gif files)
movement_gifs = [f"movement_library/gif/M{i}.gif" for i in range(1, 30)]

# Rest image path
rest_image_path = "movement_library/Rest_M0.png"

# Duration settings (in milliseconds)
INITIAL_BASELINE_MS = 5000  # First pre-movement rest (UI only; matches real timer’s fixed 5s)
movement_duration = 5000    # fallback if GIF duration is unknown
rest_between_repeats = 2000 # inter-rep rest (also used as between-movement pre-rest)
repeats_per_movement = 2    # number of times each movement is shown

# For parity with the real timer: between-movement rest equals inter-rep rest
rest_between_movements = rest_between_repeats


class GifExerciseViewer(QWidget):
    """PyQt5 application for displaying movement GIFs and guiding exercise cycles."""

    def __init__(self, gif_list):
        """
        Args:
            gif_list (list[str]): Paths to movement GIF files to display in order.
        """
        super().__init__()
        self.setWindowTitle("Practice Movements")
        self.setFixedSize(1000, 600)

        from PyQt5.QtWidgets import QHBoxLayout

        # Layout setup
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.content_layout = QHBoxLayout()

        # Preview image (next movement / current phase preview)
        self.preview_label = QLabel(self)
        self.preview_label.setScaledContents(True)
        self.preview_label.setFixedSize(280, 125)

        preview_container = QVBoxLayout()
        preview_container.addWidget(self.preview_label)
        preview_caption = QLabel("Next Phase", self)
        preview_caption.setAlignment(Qt.AlignCenter)
        preview_caption.setStyleSheet("color: black; font-size: 28px;")
        preview_container.addWidget(preview_caption)
        preview_container.setContentsMargins(0, 110, 0, 0)

        self.content_layout.addLayout(preview_container)

        # Current GIF display
        self.gif_label = QLabel(self)
        self.gif_label.setScaledContents(True)
        self.gif_label.setFixedSize(650, 325)
        self.gif_label.setStyleSheet("color: black; font-size: 36px;")
        self.content_layout.addWidget(self.gif_label, stretch=1)

        # Assemble main layout
        self.main_layout.addLayout(self.content_layout)

        # Status + fixed phase time label
        self.status_label = QLabel("", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: black; font-size: 28px;")
        self.main_layout.addWidget(self.status_label)

        self.timer_label = QLabel("", self)
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: black; font-size: 24px;")
        self.main_layout.addWidget(self.timer_label)

        # Radial progress
        self.radial = RadialProgress(diameter=40, thickness=10)
        self.main_layout.addWidget(self.radial, alignment=Qt.AlignCenter)

        # State
        self.gif_list = gif_list
        # Use PNG previews from util.images to mirror the real timer’s visuals
        self.preview_images = Images.MOVEMENT_IMAGES_A + Images.MOVEMENT_IMAGES_B
        self.current_index = 0      # which movement
        self.current_repeat = 0     # 0..repeats_per_movement-1
        self.movie = None
        self.resting = False
        self.between_movements = False
        self._radial_job_active = False

        # Start with pre-movement rest for the very first movement (fixed 5s)
        self.show_pre_movement_rest(first=True)

    # ---------------- Phase orchestration ----------------

    def _phase_start(self, duration_ms: int, color: str, time_label_prefix: str):
        """Common per-phase UI updates (color, fixed time label, radial start)."""
        # Set arc color
        self.radial.set_color(QColor(color))
        # Show fixed total phase time (no ticking)
        self.timer_label.setText(f"{time_label_prefix}: {duration_ms / 1000:.1f} s")
        # Start the arc and loop
        self.radial.start(duration_ms)
        self._radial_job_active = True
        self._radial_loop(duration_ms)

    def _radial_loop(self, remaining_ms: int):
        """Update the radial progress every 50 ms without changing the time label."""
        if not self._radial_job_active:
            return
        if remaining_ms > 0:
            self.radial.update_value(remaining_ms)
            QTimer.singleShot(50, lambda: self._radial_loop(remaining_ms - 50))
        else:
            # ensure it ends at 0
            self.radial.update_value(0)

    def _phase_finish(self, callback):
        """Finish handler to call the next step after a short tick."""
        # Stop the radial updates right before calling the next phase
        self._radial_job_active = False
        QTimer.singleShot(0, callback)

    # ---------------- Pre-movement rest ----------------

    def show_pre_movement_rest(self, first: bool = False):
        """Show pre-movement rest (UI only). First movement uses a fixed 5s."""
        self.resting = True
        self.between_movements = True

        # Preview of the upcoming movement with a red border
        if self.current_index < len(self.preview_images):
            preview_path = self.preview_images[self.current_index]
            if os.path.exists(preview_path):
                self.preview_label.setPixmap(QPixmap(preview_path))
            else:
                self.preview_label.setText("Preview not found")
        self.preview_label.setStyleSheet("border: 2px solid red;")

        # Show rest image in main area
        if os.path.exists(rest_image_path):
            rest_pixmap = QPixmap(rest_image_path)
            self.gif_label.setPixmap(rest_pixmap)
        else:
            self.gif_label.setText("Rest")

        # Status and fixed time
        self.status_label.setText(f"Resting before movement {self.current_index + 1}")

        duration_ms = INITIAL_BASELINE_MS if first else rest_between_movements
        self._phase_start(duration_ms, color="red", time_label_prefix="Time")
        # When done, start the movement
        QTimer.singleShot(duration_ms, lambda: self._phase_finish(self.start_movement))

    # ---------------- Movement ----------------

    def start_movement(self):
        """Begin/continue the movement phase for the current movement."""
        self.resting = False
        self.between_movements = False

        # Remove red border from preview during movement
        self.preview_label.setStyleSheet("border: 0px;")

        if self.current_index >= len(self.gif_list):
            self._complete_session()
            return

        gif_path = self.gif_list[self.current_index]
        if not os.path.exists(gif_path):
            print("File not found:", gif_path)
            self.gif_label.setText("Missing file")
            self.status_label.setText("Missing file")
            # On missing file, behave like a zero-duration movement and progress
            QTimer.singleShot(0, self._after_movement_phase)
            return

        # Load and play movement GIF
        self.movie = QMovie(gif_path)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.gif_label.setMovie(self.movie)
        self.movie.start()

        # During movement, preview shows the (static) rest image
        if os.path.exists(rest_image_path):
            self.preview_label.setPixmap(QPixmap(rest_image_path))
        else:
            self.preview_label.setText("Rest image not found")

        movement_name = os.path.basename(gif_path).replace(".gif", "").replace("_", " ")
        self.status_label.setText(
            f"Performing: {movement_name} (Repeat {self.current_repeat + 1}/{repeats_per_movement})"
        )

        self._phase_start(movement_duration, color="green", time_label_prefix="Time")
        # When movement duration ends, decide next step (inter-rep rest or pre-movement rest)
        QTimer.singleShot(movement_duration, lambda: self._phase_finish(self._after_movement_phase))

    def _after_movement_phase(self):
        """Called after a movement finishes; decide next phase."""
        # If more reps remain for this movement -> inter-rep rest
        if (self.current_repeat + 1) < repeats_per_movement:
            self.show_inter_rep_rest()
        else:
            # Final rep of this movement -> advance to next movement’s pre-movement rest
            self.current_repeat = 0
            self.current_index += 1
            if self.current_index >= len(self.gif_list):
                self._complete_session()
            else:
                self.show_pre_movement_rest(first=False)

    # ---------------- Inter-rep rest (UI only) ----------------

    def show_inter_rep_rest(self):
        """Show inter-repetition rest (UI only); skipped after last rep."""
        self.resting = True
        self.between_movements = False

        # Preview should show the SAME movement (next rep), no red border
        if self.current_index < len(self.preview_images):
            preview_path = self.preview_images[self.current_index]
            if os.path.exists(preview_path):
                self.preview_label.setPixmap(QPixmap(preview_path))
            else:
                self.preview_label.setText("Preview not found")
        self.preview_label.setStyleSheet("border: 0px;")

        # Show rest image in main area
        if os.path.exists(rest_image_path):
            self.gif_label.setPixmap(QPixmap(rest_image_path))
        else:
            self.gif_label.setText("Rest")

        self.status_label.setText(
            f"Resting between repeats for movement {self.current_index + 1}"
        )

        self._phase_start(rest_between_repeats, color="red", time_label_prefix="Time")
        # After inter-rep rest, increment repeat and start movement again
        def _next_rep():
            self.current_repeat += 1
            self.start_movement()

        QTimer.singleShot(rest_between_repeats, lambda: self._phase_finish(_next_rep))

    # ---------------- Session completion ----------------

    def _complete_session(self):
        """Finalize the practice session."""
        self.resting = True
        self.between_movements = False
        self.preview_label.setStyleSheet("border: 0px;")
        self.status_label.setText("Session Complete")
        self.timer_label.setText("")
        self.gif_label.setText("All movements done")
        self._radial_job_active = False
        self.radial.update_value(0)

    # ---------------- (Legacy compatibility helpers if needed) ----------------

    def play_next(self):
        """Legacy entry point; kept only for compatibility (unused)."""
        # Not used in the updated flow; real transitions use start_movement / show_pre_movement_rest / show_inter_rep_rest.
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = GifExerciseViewer(movement_gifs)
    viewer.show()
    sys.exit(app.exec_())
