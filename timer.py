import time
import tkinter as tk
from PIL import Image, ImageTk
import threading
from recording import EmgSession

# Window dimensions for both parameter and main screens
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 600

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
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)

        # Session control flags and parameters
        self.session_started = False
        self.subject_id = None
        self.perform_time = None
        self.rest_time = None
        self.num_repeats = None
        self.movement_delay = None

        # Prepare EMG recorder and start initial flush
        self.recorder = EmgSession()
        threading.Thread(target=self._initial_flush_loop, daemon=True).start()

        # Show parameter input screen
        self._build_parameter_screen()

    def _initial_flush_loop(self):
        """Continuously discard incoming data until session begins."""
        time.sleep(0.2)
        while not self.session_started:
            self.recorder.receive_and_ignore(0.1, no_print=True)
            time.sleep(0.1)

    def _build_parameter_screen(self):
        """Build the initial parameter input UI before starting session."""
        self.param_frame = tk.Frame(self.root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        self.param_frame.pack(fill="both", expand=True)

        # Configure grid to center content
        for r in (0, 7):
            self.param_frame.grid_rowconfigure(r, weight=1)
        for c in (0, 1):
            self.param_frame.grid_columnconfigure(c, weight=1)

        # Labels and entries (all start blank)
        labels = ["Subject ID:", "Perform Time (seconds):", "Rest Time Between Repetitions (seconds):",
                  "Number of Repetitions:", "Rest Time Between Movements (seconds):"]
        self.entries = []
        for i, label_text in enumerate(labels, start=1):
            tk.Label(self.param_frame, text=label_text, font=("Helvetica", 14)).grid(
                row=i, column=0, padx=20, pady=10, sticky="e"
            )
            entry = tk.Entry(self.param_frame, font=("Helvetica", 14))
            entry.grid(row=i, column=1, padx=20, pady=10, sticky="w")
            entry.bind("<KeyRelease>", lambda e: self._validate_entries())
            self.entries.append(entry)

        self.subject_id_entry = self.entries[0]
        self.perform_time_entry = self.entries[1]
        self.rest_time_entry = self.entries[2]
        self.num_repeats_entry = self.entries[3]
        self.delay_entry = self.entries[4]

        self.start_button = tk.Button(
            self.param_frame,
            text="Start Session",
            font=("Helvetica", 16),
            state=tk.DISABLED,
            command=self._start_session
        )
        self.start_button.grid(row=6, column=0, columnspan=2, pady=30)

    def _validate_entries(self):
        """Enable start button only when all fields are valid (allowing decimal seconds)."""
        sid_text = self.subject_id_entry.get().strip()
        try:
            sid_val = int(sid_text)
            if sid_val < 0:
                raise ValueError
        except ValueError:
            self.start_button.config(state=tk.DISABLED)
            return
        try:
            p = float(self.perform_time_entry.get().strip())
            r = float(self.rest_time_entry.get().strip())
            n = int(self.num_repeats_entry.get().strip())
            d = float(self.delay_entry.get().strip())
            if p <= 0 or r <= 0 or n <= 0 or d < 0:
                raise ValueError
        except ValueError:
            self.start_button.config(state=tk.DISABLED)
            return
        self.start_button.config(state=tk.NORMAL)

    def _start_session(self):
        """Read parameters (floats for times), remove input UI, and start the session."""
        self.subject_id = int(self.subject_id_entry.get().strip())
        self.recorder.make_subject_directory(self.subject_id)
        self.perform_time = float(self.perform_time_entry.get())
        self.rest_time = float(self.rest_time_entry.get())
        self.num_repeats = int(self.num_repeats_entry.get())
        self.movement_delay = float(self.delay_entry.get())

        self.session_started = True
        self.recorder.set_id(self.subject_id)
        self.param_frame.destroy()
        self._build_main_ui()
        self.run_cycle()

    def _build_main_ui(self):
        self.current_index = 0
        self.current_repeat = 0
        self.start_time = None
        self.paused = False
        self.after_last_repeat = False

        self.left_frame = tk.Frame(self.root, width=WINDOW_WIDTH//2, height=WINDOW_HEIGHT)
        self.left_frame.pack(side=tk.LEFT, fill="both", pady=20)
        self.right_frame = tk.Frame(self.root, width=WINDOW_WIDTH//2, height=WINDOW_HEIGHT)
        self.right_frame.pack(side=tk.RIGHT, fill="both", pady=20)

        self.next_image_label = tk.Label(self.left_frame)
        self.next_image_label.pack(anchor="nw", padx=10, pady=10)
        self.variable_label = tk.Label(
            self.left_frame,
            text=self.get_variables_text(),
            font=("Helvetica", 14)
        )
        self.variable_label.pack(anchor="w", padx=10, pady=10)
        self.runtime_label = tk.Label(
            self.left_frame,
            text="Runtime: 0 s",
            font=("Helvetica", 16)
        )
        self.runtime_label.pack(anchor="w", padx=10, pady=10)

        self.image_label = tk.Label(self.right_frame)
        self.image_label.pack(pady=10)
        self.time_label = tk.Label(
            self.right_frame,
            text="",
            font=("Helvetica", 16)
        )
        self.time_label.pack(pady=10)
        self.index_label = tk.Label(
            self.right_frame,
            text="",
            font=("Helvetica", 16)
        )
        self.index_label.pack(pady=10)

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
        self.stop_button = tk.Button(
            self.right_frame,
            text="Stop Session",
            font=("Helvetica", 16),
            fg="white",
            bg="black",
            command=self.stop_session
        )

    def get_variables_text(self):
        return (
            f"Subject ID: {self.subject_id}\n"
            f"Perform Time: {self.perform_time * 1000} ms\n"
            f"Rest Time: {self.rest_time * 1000} ms\n"
            f"Number of Repeats: {self.num_repeats}\n"
            f"Movement Delay: {self.movement_delay * 1000} ms"
        )

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

    def update_time(self, remaining_ms):
        """Display remaining time in milliseconds."""
        self.time_label.config(text=f"Time: {remaining_ms} ms")

    def update_index(self, mov, rep):
        self.index_label.config(text=f"Movement: {mov+1}, Repeat: {rep+1}")

    def update_runtime(self):
        if self.start_time is not None:
            elapsed = int((time.time() - self.start_time) * 1000)
            self.runtime_label.config(text=f"Runtime: {(elapsed / 1000):.0f} s")
            self.root.after(100, self.update_runtime)

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
                threading.Thread(target=self.record_rest_before_movement, daemon=True).start()
                self.countdown(int(self.movement_delay * 1000), self.start_movement)
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
            self.countdown(int(self.movement_delay * 1000), self.end_session)

    def start_movement(self):
        if self.current_repeat < self.num_repeats:
            self.show_image(movement_images[self.current_index])
            self.update_index(self.current_index, self.current_repeat)
            threading.Thread(target=self.record_emg, daemon=True).start()
            self.show_next_image(movement_images[self.current_index])
            self.countdown(int(self.perform_time * 1000), self.rest_after_movement)
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
        self.countdown(int(self.rest_time * 1000), self.start_movement)

    def countdown(self, remaining_ms, callback):
        """Countdown in milliseconds, updating every 100ms."""
        if remaining_ms > 0 and not self.paused:
            self.update_time(remaining_ms)
            # schedule next update in 100 ms
            self.root.after(100, self.countdown, remaining_ms - 100, callback)
        elif not self.paused:
            callback()

    def start_flush_loop(self):
        """Continuously discard incoming data while paused."""
        if self.paused:
            self.recorder.receive_and_ignore(0.1, no_print=True)
            self.root.after(100, self.start_flush_loop)

    def countdown_resume(self, seconds):
        if seconds > 0:
            self.resume_button.config(text=f"Resume ({seconds}s)", bg="gray")
            self.resume_button.config(state='disabled')
            self.root.after(1000, self.countdown_resume, seconds-1)
        else:
            self.resume_button.config(state='normal', text="Resume", bg="green")

    def stop_exercise(self):
        self.paused = True
        self.current_repeat = 0
        self.after_last_repeat = False

        self.show_image(rest_image)
        self.show_next_image(movement_images[self.current_index])
        self.index_label.config(text="Press Resume or Stop Session")
        self.time_label.config(text="")

        self.pause_button.pack_forget()
        self.resume_button.pack(pady=10)
        self.stop_button.pack(pady=10)
        self.countdown_resume(int(self.movement_delay))

        self.start_flush_loop()

    def resume_exercise(self):
        if self.paused:
            self.paused = False
            self.resume_button.pack_forget()
            self.stop_button.pack_forget()
            self.pause_button.pack(pady=10)
            self.show_image(rest_image)
            self.show_next_image(movement_images[self.current_index])
            self.index_label.config(
                text=f"Resting before movement {self.current_index+1}"
            )
            self.time_label.config(text="")


    def stop_session(self):
        self.recorder.finish()
        self.root.destroy()

    def end_session(self):
        # Send stop command to recorder
        self.recorder.finish()
        # Update UI to indicate completion
        self.index_label.config(text="Session Complete")
        self.time_label.config(text="")
        self.runtime_label.config(
            text=f"Total Runtime: {int(time.time() - self.start_time)} seconds"
        )
        # Repurpose pause button as close button
        self.pause_button.config(text="Close", command=self.stop_session, fg="white", bg="black")
        # Remove other controls
        self.resume_button.pack_forget()
        self.stop_button.pack_forget()
        # Ensure close button is visible
        self.pause_button.pack(pady=10)

    def record_emg(self):
        self.recorder.emg_recording(
            self.perform_time,
            self.rest_time,
            self.current_index + 1,
            self.current_repeat + 1
        )

    def record_rest_before_movement(self):
        self.recorder.record_initial_rest(
            self.movement_delay,
            self.current_index + 1,
            self.perform_time
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()
