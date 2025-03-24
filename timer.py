
import time
import tkinter as tk

from PIL import Image, ImageTk
import threading
from recording import EmgSession

perform_time = 2  # seconds to perform one movement
rest_time = 2  # seconds to rest between movements
num_repeats = 3  # number of repeats for each movement

# List of movement image filenames
movement_images = [
    "movement_library/EA/Index_flexion_M1.png",
    "movement_library/EA/Index_Extension_M2.png",
    "movement_library/EA/Middle_Flexion_M3.png",
    "movement_library/EA/Middle_Extension_M4.png",
    "movement_library/EA/Ring_Flexion_M5.png",
    "movement_library/EA/Ring_Extension_M6.png",
    "movement_library/EA/Little_Flexion_M7.png",
    "movement_library/EA/Little_Extension_M8.png",
    "movement_library/EA/Thurmb_Adduction_M9.png",
    "movement_library/EA/Thurmb_Abduction_M10.png",
    "movement_library/EA/Thurmb_Flexion_M11.png",
    "movement_library/EA/Thurmb_Extension_M12.png"
]

# Rest image filename
rest_image = "movement_library/Rest_M0.png"


class ExerciseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Exercise Timer")

        # Create the main frames
        self.left_frame = tk.Frame(root)
        self.left_frame.pack(side=tk.LEFT, padx=20, pady=20)

        self.right_frame = tk.Frame(root)
        self.right_frame.pack(side=tk.RIGHT, padx=20, pady=20)

        # Left Frame for Variables, Runtime, and Preview Image
        self.next_image_label = tk.Label(self.left_frame)
        self.next_image_label.pack(anchor="nw")

        self.variable_label = tk.Label(self.left_frame, text=self.get_variables_text(), font=("Helvetica", 14))
        self.variable_label.pack(anchor="w")

        self.runtime_label = tk.Label(self.left_frame, text="Runtime: 0 seconds", font=("Helvetica", 16))
        self.runtime_label.pack(anchor="w")

        # Right Frame for Image, Time, and Movement Index
        self.image_label = tk.Label(self.right_frame)
        self.image_label.pack()

        self.time_label = tk.Label(self.right_frame, text="", font=("Helvetica", 16))
        self.time_label.pack()

        self.index_label = tk.Label(self.right_frame, text="", font=("Helvetica", 16))
        self.index_label.pack()

        # Buttons for Stop and Resume
        self.stop_button = tk.Button(self.right_frame, text="Stop", font=("Helvetica", 16), fg="black", bg="red",
                                     command=self.stop_exercise)
        self.stop_button.pack(pady=10)

        self.resume_button = tk.Button(self.right_frame, text="Resume", font=("Helvetica", 16), fg="black", bg="green",
                                       command=self.resume_exercise)
        self.resume_button.pack(pady=10)

        # State variables
        self.current_index = 0
        self.current_repeat = 0
        self.start_time = None
        self.paused_time = None
        self.total_paused_time = 0
        self.running = False
        self.paused = False

        # Flags to indicate where the exercise was paused
        self.after_last_repeat = False

        # New fields for emg recording
        self.recorder = EmgSession()

        # Start the EMG recording in a separate thread
        movement, repetition = self.current_index + 1, self.current_repeat + 1
        self.run_cycle()


    def get_variables_text(self):
        """Return a formatted string displaying the variables."""
        return (f"Perform Time: {perform_time} seconds\n"
                f"Rest Time: {rest_time} seconds\n"
                f"Number of Repeats: {num_repeats}")

    def show_image(self, image_path):
        """Display an image."""
        img = Image.open(image_path)
        img_tk = ImageTk.PhotoImage(img)
        self.image_label.config(image=img_tk)
        self.image_label.image = img_tk

    def show_next_image(self, image_path):
        """Display the next movement image as a small preview."""
        img = Image.open(image_path)
        img = img.resize((300, 100))  # Small preview size
        img_tk = ImageTk.PhotoImage(img)
        self.next_image_label.config(image=img_tk)
        self.next_image_label.image = img_tk

    def update_time(self, remaining_time):
        """Update the time display."""
        self.time_label.config(text=f"Time: {remaining_time} seconds")

    def update_index(self, current_movement, current_repeat):
        """Update the movement index display."""
        self.index_label.config(
            text=f"Movement: {current_movement + 1}, Repeat: {current_repeat + 1}"
        )

    def update_runtime(self):
        """Update the runtime display."""
        if self.running:
            elapsed_time = int(time.time() - self.start_time)
            self.runtime_label.config(text=f"Runtime: {elapsed_time} seconds")
            self.root.after(1000, self.update_runtime)

    def run_cycle(self):
        """Run the full exercise cycle."""
        if self.start_time is None:
            self.start_time = time.time()
            self.running = True
            self.update_runtime()

        if self.current_index < len(movement_images):
            if self.current_repeat == 0 and not self.after_last_repeat:
                # Initial 5s rest before starting the movement
                self.show_image(rest_image)
                threading.Thread(target=self.delay_emg_start, daemon=True).start()
                self.next_image_label.config(image='')  # Clear the next image
                self.countdown(5, self.start_movement)
            elif self.after_last_repeat:
                # Continue after last repeat's 5s rest and resume to next movement
                self.after_last_repeat = False
                self.current_repeat = 0
                self.current_index += 1
                self.run_cycle()  # Ensure this is called here
            else:
                self.start_movement()
        else:
            # Final 5s rest after all movements
            self.show_image(rest_image)
            self.next_image_label.config(image='')  # Clear the next image
            self.countdown(5, self.end_session)

    def start_movement(self):
        """Start the movement and handle repeats."""
        if self.current_repeat < num_repeats - 1:
            self.show_image(movement_images[self.current_index])
            self.update_index(self.current_index, self.current_repeat)
            threading.Thread(target=self.record_emg, daemon=True).start()

            if self.current_repeat == num_repeats - 1:  # Last repeat
                next_index = (self.current_index + 1) % len(movement_images)
                self.show_next_image(movement_images[next_index])
                self.countdown(perform_time, self.final_rest)
            else:
                self.countdown(perform_time, self.rest_after_movement)
        else:
            self.current_repeat = 0
            self.current_index += 1
            self.run_cycle()

    def rest_after_movement(self):
        """Rest between repeats."""
        self.current_repeat += 1
        self.show_image(rest_image)
        # threading.Thread(target=self.ignore_data, daemon=True).start()
        self.countdown(rest_time, self.start_movement)

    def final_rest(self):
        """Final 5s rest after last repeat of a movement."""
        self.show_image(rest_image)
        self.countdown(5, self.pause_cycle)
        self.after_last_repeat = True

    def countdown(self, duration, callback):
        """Display the countdown and execute callback after."""
        if duration > 0 and not self.paused:
            self.update_time(duration)
            self.root.after(1000, self.countdown, duration - 1, callback)
        elif not self.paused:
            callback()

    def pause_cycle(self):
        """Pause the cycle after final rest."""
        self.after_last_repeat = True
        self.paused = True
        self.paused_time = time.time()

    def resume_exercise(self):
        """Resume the cycle after pausing."""
        if self.paused:
            self.paused = False
            self.running = True
            if self.paused_time:
                self.total_paused_time += time.time() - self.paused_time
                self.paused_time = None
            self.run_cycle()

    def stop_exercise(self):
        """Stop the exercise cycle."""
        self.paused = True
        self.paused_time = time.time()

    def end_session(self):
        self.running = False
        self.update_index("All", "Complete")
        self.time_label.config(text="")
        self.runtime_label.config(text=f"Total Runtime: {int(time.time() - self.start_time)} seconds")

    def record_emg(self):
        """record EMG data."""
        self.recorder.emg_recording(perform_time + rest_time, self.current_index + 1, self.current_repeat + 1)

    def ignore_data(self):
        """record EMG data."""
        self.recorder.receive_and_ignore(rest_time)

    def delay_emg_start(self):
        """record EMG data."""
        self.recorder.receive_and_ignore(5)


if __name__ == "__main__":
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()
