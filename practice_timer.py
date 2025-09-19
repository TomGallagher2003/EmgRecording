import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QTimer, QRectF

from util.images import Images


class RadialProgress(QWidget):
    def __init__(self, diameter=100, thickness=8, parent=None):
        super().__init__(parent)
        self.diameter   = diameter
        self.thickness  = thickness
        self.setFixedSize(diameter, diameter)
        self._total_ms     = 1
        self._remaining_ms = 1

    def start(self, total_ms: int):
        self._total_ms = total_ms
        self._remaining_ms = total_ms
        self.update()

    def update_value(self, remaining_ms: int):
        self._remaining_ms = remaining_ms
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.thickness/2,
                      self.thickness/2,
                      self.diameter - self.thickness,
                      self.diameter - self.thickness)
        pen = QPen(QColor('#ddd'), self.thickness)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        if self._total_ms > 0:
            frac = self._remaining_ms / self._total_ms
            span = int(360 * frac * 16)
            pen.setColor(QColor('#525c63'))
            painter.setPen(pen)
            painter.drawArc(rect, 90*16, -span)


# Movement GIFs (change these to actual paths to your .gif files)
# replace your four‑item list with this:
movement_gifs = [f"movement_library/gif/M{i}.gif" for i in range(1, 30)]


# Rest image path
rest_image_path = "movement_library/Rest_M0.png"

# Duration settings (in milliseconds)
movement_duration = 5000  # fallback if GIF duration is unknown
rest_between_repeats = 2000
rest_between_movements = 4000
repeats_per_movement = 2  # number of times each movement is shown


class GifExerciseViewer(QWidget):
    def __init__(self, gif_list):
        super().__init__()
        self.setWindowTitle("Practice Movements")
        self.setFixedSize(1000, 600)

        from PyQt5.QtWidgets import QHBoxLayout

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.content_layout = QHBoxLayout()

        self.status_label = QLabel("", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: black; font-size: 28px;")

        # create the preview image widget
        self.preview_label = QLabel(self)
        self.preview_label.setScaledContents(True)
        self.preview_label.setFixedSize(280, 125)

        # put it in its own vertical layout so we can add a caption beneath it
        preview_container = QVBoxLayout()
        preview_container.addWidget(self.preview_label)

        # add the caption
        preview_caption = QLabel("Next Phase", self)
        preview_caption.setAlignment(Qt.AlignCenter)
        preview_caption.setStyleSheet("color: black; font-size: 28px;")
        preview_container.addWidget(preview_caption)
        preview_container.setContentsMargins(0, 110, 0, 0)

        # insert that container into the main content layout
        self.content_layout.addLayout(preview_container)

        self.gif_label = QLabel(self)
        self.gif_label.setScaledContents(True)
        self.gif_label.setFixedSize(650, 325)
        self.gif_label.setStyleSheet("color: black; font-size: 36px;")

        self.content_layout.addWidget(self.gif_label, stretch=1)
        self.gif_label.show()
        self.main_layout.addLayout(self.content_layout)
        self.main_layout.addWidget(self.status_label)
        self.radial = RadialProgress(diameter=40, thickness=10)
        self.main_layout.addWidget(self.radial, alignment=Qt.AlignCenter)

        self.timer_label = QLabel("", self)
        self.timer_label.setStyleSheet("color: black; font-size: 24px;")

        self.gif_list = gif_list
        self.preview_images = Images.MOVEMENT_IMAGES_A + Images.MOVEMENT_IMAGES_B
        self.current_index = 0
        self.current_repeat = -1
        self.movie = None
        self.resting = False
        self.between_movements = False

        self.between_movements = True
        self.resting = True
        self.show_rest(rest_between_movements)

    def play_next(self):
        if self.resting:
            self.resting = False
            self.current_repeat += 1

            if self.current_repeat >= repeats_per_movement:
                self.current_repeat = 0
                self.current_index += 1
                self.between_movements = True
                self.show_countdown(rest_between_movements, self.play_next)
                return
            else:
                self.play_next()
            return

        if self.current_index >= len(self.gif_list):
            self.status_label.setText("Session Complete")
            self.gif_label.setText("All movements done")
            self.status_label.setText("")
            return

        gif_path = self.gif_list[self.current_index]
        print(f"Loading: {gif_path} (Repeat {self.current_repeat + 1}/{repeats_per_movement})")

        if not os.path.exists(gif_path):
            print("File not found:", gif_path)
            self.gif_label.setText("Missing file")
            self.status_label.setText("Missing file")
            self.resting = True
            self.show_countdown(rest_between_repeats, self.play_next)
            return

        self.movie = QMovie(gif_path)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.gif_label.setMovie(self.movie)
        self.movie.start()

        # During movement, preview shows the rest image
        if os.path.exists(rest_image_path):
            rest_pixmap = QPixmap(rest_image_path)
            self.preview_label.setPixmap(rest_pixmap)
        else:
            self.preview_label.setText("Rest image not found")

        movement_name = os.path.basename(gif_path).replace(".gif", "").replace("_", " ")
        self.status_label.setText(
            f"Performing: {movement_name} (Repeat {self.current_repeat + 1}/{repeats_per_movement})")

        self.show_countdown(movement_duration, self.show_rest)

    def show_rest(self, time=None):
        print("Showing rest image")
        # Set preview image to upcoming movement (if available)
        if self.current_index < len(self.preview_images):
            preview_path = self.preview_images[self.current_index] if not self.current_repeat == repeats_per_movement - 1 else rest_image_path
            if os.path.exists(preview_path):
                pixmap = QPixmap(preview_path)
                self.preview_label.setPixmap(pixmap)
            else:
                self.preview_label.setText("Preview not found")
        if os.path.exists(rest_image_path):
            rest_movie = QMovie(rest_image_path)
            self.gif_label.setMovie(rest_movie)
            rest_movie.start()
        else:
            self.gif_label.setText("Rest")
        self.resting = True
        time = time if time is not None else rest_between_repeats
        self.show_countdown(time, self.play_next)

    def show_countdown(self, duration_ms, callback):
        # reset radial arc
        self.radial.start(duration_ms)
        self._radial_loop(duration_ms)
        if self.current_index < len(self.preview_images) and self.between_movements:
            preview_path = self.preview_images[self.current_index]
            if os.path.exists(preview_path):
                pixmap = QPixmap(preview_path)
                self.preview_label.setPixmap(pixmap)
            else:
                self.preview_label.setText("Preview not found")
        steps = duration_ms // 1000
        self._initial_steps = steps
        self._countdown(duration_ms, callback)

    def _countdown(self, milliseconds_left, callback):
        if self.between_movements:
            msg = f"Resting before movement {self.current_index + 1}"
            if self.current_index == 4:
                msg = f"Final Rest"

        elif self.resting:
            msg = "Resting between repeats"
        else:
            msg = f"Repeat {self.current_repeat + 1} of movement {self.current_index + 1}"

        self.status_label.setText(f"{msg} \n {self._initial_steps}s")

        if milliseconds_left > 0:
            QTimer.singleShot(10, lambda: self._countdown(milliseconds_left - 10, callback))
        else:
            self.timer_label.setText("")
            self.between_movements = False
            callback()
    def _radial_loop(self, remaining_ms):
        if remaining_ms > 0:
            self.radial.update_value(remaining_ms)
            QTimer.singleShot(10, lambda: self._radial_loop(remaining_ms - 10))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = GifExerciseViewer(movement_gifs)
    viewer.show()
    sys.exit(app.exec_())
