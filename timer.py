import time
import tkinter as tk
from PIL import Image, ImageTk
import threading
from recording import EmgSession

perform_time = 2  # seconds to perform one movement
rest_time = 2     # seconds to rest between movements
num_repeats = 3   # number of repeats for each movement
movement_delay = 5  # seconds before resume is enabled

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

        # Left Frame elements
        self.next_image_label = tk.Label(self.left_frame)
        self.next_image_label.pack(anchor="nw")
        self.variable_label = tk.Label(
            self.left_frame,
            text=self.get_variables_text(),
            font=("Helvetica", 14)
        )
        self.variable_label.pack(anchor="w")
        self.runtime_label = tk.Label(
            self.left_frame,
            text="Runtime: 0 seconds",
            font=("Helvetica", 16)
        )
        self.runtime_label.pack(anchor="w")

        # Right Frame elements
        self.image_label = tk.Label(self.right_frame)
        self.image_label.pack()
        self.time_label = tk.Label(
            self.right_frame,
            text="",
            font=("Helvetica", 16)
        )
        self.time_label.pack()
        self.index_label = tk.Label(
            self.right_frame,
            text="",
            font=("Helvetica", 16)
        )
        self.index_label.pack()

        # Pause, Resume, and Stop buttons
        self.pause_button = tk.Button(
            self.right_frame,
            text="Pause",
            font=("Helvetica", 16),
            fg="black",
            bg="red",
            command=self.stop_exercise
        )
        self.pause_button.pack(pady=10)
        self.resume_button = tk.Button(
            self.right_frame,
            text="Resume",
            font=("Helvetica", 16),
            fg="black",
            bg="green",
            command=self.resume_exercise
        )
        # Stop button to end session when paused
        self.stop_button = tk.Button(
            self.right_frame,
            text="Stop Session",
            font=("Helvetica", 16),
            fg="white",
            bg="black",
            command=self.stop_session
        )

        # State variables
        self.current_index = 0
        self.current_repeat = 0
        self.start_time = None
        self.paused = False
        self.after_last_repeat = False

        # EMG recorder
        self.recorder = EmgSession()
        time.sleep(0.5)
        threading.Thread(target=self.clear_initial, daemon=True).start()
        time.sleep(0.5)
        # Start application
        self.run_cycle()

    def get_variables_text(self):
        return (f"Perform Time: {perform_time} seconds\n"  
                f"Rest Time: {rest_time} seconds\n"   
                f"Number of Repeats: {num_repeats}")

    def show_image(self, path):
        img = Image.open(path)
        img_tk = ImageTk.PhotoImage(img)
        self.image_label.config(image=img_tk)
        self.image_label.image = img_tk

    def show_next_image(self, path):
        img = Image.open(path)
        img = img.resize((300, 100))
        img_tk = ImageTk.PhotoImage(img)
        self.next_image_label.config(image=img_tk)
        self.next_image_label.image = img_tk

    def update_time(self, remaining):
        self.time_label.config(text=f"Time: {remaining} seconds")

    def update_index(self, mov, rep):
        self.index_label.config(text=f"Movement: {mov+1}, Repeat: {rep+1}")

    def update_runtime(self):
        if self.start_time is not None:
            elapsed = int(time.time() - self.start_time)
            self.runtime_label.config(text=f"Runtime: {elapsed} seconds")
            self.root.after(1000, self.update_runtime)

    def run_cycle(self):
        if self.start_time is None:
            self.start_time = time.time()
            self.update_runtime()

        if self.current_index < len(movement_images):
            if self.current_repeat == 0 and not self.after_last_repeat:
                self.show_image(rest_image)
                self.show_next_image(movement_images[self.current_index])
                self.index_label.config(
                    text=f"Resting before movement {self.current_index+1}"
                )
                threading.Thread(
                    target=self.record_rest_before_movement,
                    daemon=True
                ).start()
                self.countdown(5, self.start_movement)
            elif self.after_last_repeat:
                self.after_last_repeat = False
                self.current_repeat = 0
                self.current_index += 1
                self.run_cycle()
            else:
                self.start_movement()
        else:
            self.show_image(rest_image)
            self.show_next_image(movement_images[-1])
            self.index_label.config(text="Session Complete")
            self.countdown(5, self.end_session)

    def start_movement(self):
        if self.current_repeat < num_repeats:
            self.show_image(movement_images[self.current_index])
            self.update_index(self.current_index, self.current_repeat)
            threading.Thread(
                target=self.record_emg,
                daemon=True
            ).start()
            self.show_next_image(movement_images[self.current_index])
            self.countdown(perform_time, self.rest_after_movement)
        else:
            self.current_repeat = 0
            self.current_index += 1
            self.run_cycle()

    def rest_after_movement(self):
        self.current_repeat += 1
        self.show_image(rest_image)
        self.show_next_image(movement_images[self.current_index])
        self.index_label.config(
            text=f"Resting between repeats for movement {self.current_index+1}"
        )
        self.countdown(rest_time, self.start_movement)

    def countdown(self, duration, callback):
        if duration > 0 and not self.paused:
            self.update_time(duration)
            self.root.after(1000, self.countdown, duration-1, callback)
        elif not self.paused:
            callback()

    def start_flush_loop(self):
        """Continuously discard incoming data while paused."""
        if self.paused:
            self.recorder.receive_and_ignore(0.1, no_print=True)
            self.root.after(100, self.start_flush_loop)

    def countdown_resume(self, seconds):
        """Disable resume button, gray it out, and show countdown on it."""
        if seconds > 0:
            self.resume_button.config(text=f"Resume ({seconds}s)", bg="grey")
            self.resume_button.config(state='disabled')
            self.root.after(1000, self.countdown_resume, seconds-1)
        else:
            self.resume_button.config(state='normal', text="Resume", bg="green")

    def stop_exercise(self):
        self.paused = True
        self.current_repeat = 0
        self.after_last_repeat = False

        # update labels
        self.show_image(rest_image)
        self.show_next_image(movement_images[self.current_index])
        self.index_label.config(
            text=f"Press Resume or Stop Session"
        )
        self.time_label.config(text="")

        # toggle buttons: hide pause, show resume and stop
        self.pause_button.pack_forget()
        self.resume_button.pack(pady=10)
        self.stop_button.pack(pady=10)
        self.countdown_resume(movement_delay)

        # start continuous flushing while paused
        self.start_flush_loop()

    def resume_exercise(self):
        if self.paused:
            self.paused = False

            # restore UI and buttons
            self.resume_button.pack_forget()
            self.stop_button.pack_forget()
            self.pause_button.pack(pady=10)
            self.show_image(rest_image)
            self.show_next_image(movement_images[self.current_index])
            self.index_label.config(
                text=f"Resting before movement {self.current_index+1}"
            )
            self.time_label.config(text="")

            threading.Thread(
                target=self.record_rest_before_movement,
                daemon=True
            ).start()
            self.countdown(5, self.start_movement)

    def stop_session(self):
        # finish EMG recording and close app
        self.recorder.finish()
        self.root.destroy()

    def end_session(self):
        self.update_index("All", "Complete")
        self.time_label.config(text="")
        self.runtime_label.config(
            text=f"Total Runtime: {int(time.time() - self.start_time)} seconds"
        )

    def record_emg(self):
        self.recorder.emg_recording(
            perform_time,
            rest_time,
            self.current_index+1,
            self.current_repeat+1
        )

    def record_rest_before_movement(self):
        self.recorder.record_initial_rest(movement_delay, self.current_index+1)

    def clear_initial(self):
        for i in range(5):
            self.recorder.receive_and_ignore(0.1)


if __name__ == "__main__":
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()
