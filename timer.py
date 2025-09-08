import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
from recording import EmgSession
from util.data_validation import validate_data
from util.images import Images

# Window dimensions for both parameter and main screens
SIZE = 100
WINDOW_WIDTH = 10 * SIZE
WINDOW_HEIGHT = 6 * SIZE


# Rest image filename
rest_image = Images.REST

class ExerciseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Exercise Timer")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)

        # Device selections
        self.use_emg = False
        self.use_eeg = False

        # Session parameters
        self.session_started = False
        self.subject_id = None
        self.perform_time = None
        self.rest_time = None
        self.num_repeats = None
        self.movement_delay = None
        self.exercise_set = None
        self.exercise_set_var = tk.StringVar()
        self.movement_images = []
        self.index_offset = 0

        # Pause/resume state
        self.paused = False
        self.remaining_ms = 0
        self.total_ms = 0
        self.phase_callback = None

        # Recorder (created after device selection confirmation, always)
        self.recorder = None

        # Show device selection screen FIRST
        self._build_device_screen()

    # -------- Device selection screen (must select at least one) --------
    def _build_device_screen(self):
        frame = tk.Frame(self.root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        frame.pack(fill='both', expand=True)
        self.device_frame = frame

        for r in (0, 4):
            frame.grid_rowconfigure(r, weight=1)
        for c in (0, 1):
            frame.grid_columnconfigure(c, weight=1)

        title = tk.Label(frame, text="Select Connected Devices", font=("Helvetica", 20))
        title.grid(row=1, column=0, columnspan=2, pady=20)

        self.emg_var = tk.BooleanVar(value=False)
        self.eeg_var = tk.BooleanVar(value=False)

        emg_cb = tk.Checkbutton(frame, text="EMG", variable=self.emg_var, font=("Helvetica", 16),
                                command=self._validate_device_selection)
        eeg_cb = tk.Checkbutton(frame, text="EEG", variable=self.eeg_var, font=("Helvetica", 16),
                                command=self._validate_device_selection)
        emg_cb.grid(row=2, column=0, pady=10)
        eeg_cb.grid(row=2, column=1, pady=10)

        self.device_error = tk.Label(frame, text="", fg="red", font=("Helvetica", 12))
        self.device_error.grid(row=3, column=0, columnspan=2, pady=5)

        self.device_continue_btn = tk.Button(frame, text="Continue", font=("Helvetica", 16),
                                             state='disabled', command=self._confirm_devices)
        self.device_continue_btn.grid(row=4, column=0, columnspan=2, pady=30)

    def _validate_device_selection(self):
        if self.emg_var.get() or self.eeg_var.get():
            self.device_continue_btn.config(state='normal')
            self.device_error.config(text="")
        else:
            self.device_continue_btn.config(state='disabled')
            self.device_error.config(text="Please select at least one device (EEG and/or EMG).")

    def _confirm_devices(self):
        # Save selections
        self.use_emg = self.emg_var.get()
        self.use_eeg = self.eeg_var.get()
        self.device_continue_btn.config(state='disabled')
        # Create recording session now
        self.recorder = EmgSession(self.use_emg, self.use_eeg)

        # Do quick data check before proceeding
        if not self.quick_device_check():
            self.device_error.config(text="Device check failed. Reboot the Syncstation and ensure the selected devices are connected."
                                          "\n The software will now close")
            self.root.after(3000, self.stop_session)
        else:

            # Start initial flush loop after recorder exists
            threading.Thread(target=self._initial_flush_loop, daemon=True).start()

            # Proceed to parameter screen
            self.device_frame.destroy()
            self._build_parameter_screen()

    def quick_device_check(self):
        try:
            self.recorder.receive_and_ignore(2.5)
            test_data = self.recorder.get_record(0.1)
            if not validate_data(test_data, self.use_emg, self.use_eeg):
                return False
            return True
        except Exception as e:
            print(f"[validate_data] Caught exception: {e!r}")
            print(f"Type: {type(e).__name__}")
        return False

    def _initial_flush_loop(self):
        time.sleep(0.2)
        while not self.session_started:
            self.recorder.receive_and_ignore(0.1, no_print=True)
            time.sleep(0.1)

    def _build_parameter_screen(self):
        frame = tk.Frame(self.root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        frame.pack(fill='both', expand=True)
        self.param_frame = frame
        for r in (0,8): frame.grid_rowconfigure(r, weight=1)
        for c in (0,1): frame.grid_columnconfigure(c, weight=1)

        labels = [
            "Subject ID:",
            "Perform Time (seconds):",
            "Rest Time Between Repetitions (seconds):",
            "Number of Repetitions:",
            "Rest Time Between Movements (seconds):"
        ]
        self.entries = []
        for i, text in enumerate(labels, start=1):
            tk.Label(frame, text=text, font=("Helvetica",14)).grid(row=i, column=0, sticky='e', padx=20, pady=10)
            entry = tk.Entry(frame, font=("Helvetica",14))
            entry.grid(row=i, column=1, sticky='w', padx=20, pady=10)
            entry.bind('<KeyRelease>', lambda e: self._validate_entries())
            self.entries.append(entry)
        (self.subject_id_entry,
         self.perform_time_entry,
         self.rest_time_entry,
         self.num_repeats_entry,
         self.delay_entry) = self.entries

        tk.Label(frame, text="Exercise Set (A, B, AB):", font=("Helvetica",14))\
            .grid(row=6, column=0, sticky='e', padx=20, pady=10)
        combo = ttk.Combobox(frame, textvariable=self.exercise_set_var, font=("Helvetica",14),
                             values=["A","B","AB"], state='readonly')
        combo.grid(row=6, column=1, sticky='w', padx=20, pady=10)
        combo.bind('<<ComboboxSelected>>', lambda e: self._validate_entries())
        self.exercise_set_combobox = combo

        btn = tk.Button(frame, text="Start Session", font=("Helvetica",16),
                        state='disabled', command=self._start_session)
        btn.grid(row=7, column=0, columnspan=2, pady=30)
        self.start_button = btn

    def _validate_entries(self):
        try:
            if int(self.subject_id_entry.get().strip()) < 0: raise ValueError
            if float(self.perform_time_entry.get().strip()) <= 0: raise ValueError
            if float(self.rest_time_entry.get().strip()) <= 0: raise ValueError
            if int(self.num_repeats_entry.get().strip()) <= 0: raise ValueError
            if float(self.delay_entry.get().strip()) < 0: raise ValueError
            if self.exercise_set_var.get() not in ("A","B","AB"): raise ValueError
        except Exception:
            self.start_button.config(state='disabled')
            return
        self.start_button.config(state='normal')

    def _start_session(self):
        # Read params
        self.subject_id = int(self.subject_id_entry.get().strip())
        self.perform_time = float(self.perform_time_entry.get())
        self.rest_time = float(self.rest_time_entry.get())
        self.num_repeats = int(self.num_repeats_entry.get())
        self.movement_delay = float(self.delay_entry.get())
        self.exercise_set = self.exercise_set_var.get()
        # Configure movement list
        if self.exercise_set == 'A':
            self.movement_images = Images.MOVEMENT_IMAGES_A
            self.index_offset = 0
        elif self.exercise_set == 'B':
            self.movement_images = Images.MOVEMENT_IMAGES_B
            self.index_offset = 12
        else:
            self.movement_images = Images.MOVEMENT_IMAGES_A + Images.MOVEMENT_IMAGES_B
            self.index_offset = 0
        # Setup recorder (directory/id) — recorder already exists
        self.recorder.make_subject_directory(self.subject_id, exercise_set=self.exercise_set)
        self.recorder.set_id(self.subject_id)
        self.session_started = True

        # Switch to main UI
        self.param_frame.destroy()
        self._build_main_ui()
        self.run_cycle()

    def _build_main_ui(self):
        self.current_index = 0
        self.current_repeat = 0
        self.after_last_repeat = False
        self.start_time = None
        self.prev = time.time()

        left = tk.Frame(self.root, width=WINDOW_WIDTH//2, height=WINDOW_HEIGHT)
        left.pack(side='left', fill='both', pady=50, padx=30)
        right = tk.Frame(self.root, width=WINDOW_WIDTH//2, height=WINDOW_HEIGHT)
        right.pack(side='right', fill='both', pady=50)
        self.left_frame, self.right_frame = left, right

        self.next_image_label = tk.Label(left)
        self.next_image_label.pack(anchor='n', padx=10, pady=10)
        self.variable_label = tk.Label(left, text=self.get_variables_text(), font=("Helvetica",14))
        self.variable_label.pack(anchor='w', padx=10, pady=10)
        self.runtime_label = tk.Label(left, text="Runtime: 0 s", font=("Helvetica",16))
        self.runtime_label.pack(anchor='w', padx=10, pady=10)

        self.image_label = tk.Label(right)
        self.image_label.pack(pady=10, padx=WINDOW_WIDTH * 0.1)

        self.time_label = tk.Label(right, text="", font=("Helvetica",16))
        self.time_label.pack(pady=10)
        self.index_label = tk.Label(right, text="", font=("Helvetica",16))
        self.index_label.pack(pady=10)

        # Radial countdown indicator
        self.canvas = tk.Canvas(self.right_frame, width=50, height=50)
        self.canvas.pack(pady=10)
        self.canvas.create_oval(10, 10, 40, 40, outline='#ddd', width=8)
        self.arc = self.canvas.create_arc(10, 10, 40, 40, start=90, extent=0,
                                          style='arc', width=8)

        self.pause_button = tk.Button(right, text="Pause", font=("Helvetica",16),
                                      fg="black", bg="red", command=self.pause_exercise)
        self.pause_button.pack(pady=10)

        self.resume_button = tk.Button(right, text="Resume", font=("Helvetica",16),
                                       fg="black", bg="green", command=self.resume_exercise)
        self.stop_button = tk.Button(right, text="Stop Session", font=("Helvetica",16),
                                     fg="white", bg="black", command=self.stop_session)

    def get_variables_text(self):
        return (f"Subject ID: {self.subject_id}\n"
                f"Set: {self.exercise_set}\n"
                f"Perform Time: {self.perform_time*1000} ms\n"
                f"Rest Time: {self.rest_time*1000} ms\n"
                f"Repeats: {self.num_repeats}\n"
                f"Movement Delay: {self.movement_delay*1000} ms")

    def show_image(self, path):
        img = Image.open(path)
        max_w = WINDOW_WIDTH * 0.7
        max_h = WINDOW_HEIGHT // 2.3
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self.image_label.config(image=tkimg)
        self.image_label.image = tkimg

    def show_next_image(self, path):
        img = Image.open(path)
        max_w = WINDOW_WIDTH * 0.7 // 2
        max_h = WINDOW_HEIGHT // 2.3 // 2
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self.next_image_label.config(image=tkimg)
        self.next_image_label.image = tkimg

    def update_time(self, remaining_ms):
        self.time_label.config(text=f"Time: {(remaining_ms / 1000):.1f} s")

    def update_index(self, mov, rep):
        number = self.index_offset + mov + 1
        self.index_label.config(text=f"Movement: {number}, Repeat: {rep+1}")

    def update_runtime(self):
        if self.start_time is not None:
            elapsed = int((time.time() - self.start_time) * 1000)
            self.runtime_label.config(text=f"Runtime: {elapsed//1000} s")
            self.root.after(1000, self.update_runtime)

    def run_cycle(self):
        if self.start_time is None:
            self.start_time = time.time()
            self.update_runtime()

        if self.current_index < len(self.movement_images):
            # initial rest before first rep
            if self.current_repeat == 0 and not self.after_last_repeat:
                remainder = int(self.movement_delay * 1000)
                self.index_label.config(text=f"Resting before movement {self.current_index + 1}")
                self.update_time(remainder)
                if not self.paused:
                    threading.Thread(target=self.record_rest_before_movement, daemon=True).start()
                self.show_image(rest_image)
                self.show_next_image(self.movement_images[self.current_index])
                self.start_phase(remainder, self.start_movement)

            # move to next movement
            elif self.after_last_repeat:
                self.after_last_repeat = False
                self.current_repeat = 0
                self.current_index += 1
                self.run_cycle()

            # continue into movement
            else:
                self.start_movement()

        else:
            # session complete
            self.show_image(rest_image)
            self.show_next_image(self.movement_images[-1])
            self.index_label.config(text="Session Complete")
            self.start_phase(int(self.movement_delay * 1000), self.end_session)

    def start_movement(self):
        if self.current_repeat < self.num_repeats:
            self.show_image(self.movement_images[self.current_index])
            self.update_index(self.current_index, self.current_repeat)
            if not self.paused:
                threading.Thread(target=self.record_emg, daemon=True).start()
            self.show_next_image(self.movement_images[self.current_index])
            self.start_phase(int(self.perform_time * 1000), self.rest_after_movement)
        else:
            self.current_repeat = 0
            self.current_index += 1
            self.run_cycle()

    def start_phase(self, duration_ms, callback):
        self.canvas.itemconfigure(self.arc, extent=0)
        self.phase_callback = callback
        self.total_ms = duration_ms
        self.remaining_ms = duration_ms
        self.update_time(duration_ms)
        self._arc_countdown(duration_ms, duration_ms)

    def _arc_countdown(self, remaining_ms, total_ms, start_time=0):
        if start_time == 0:
            start_time = time.time()
        remaining = total_ms - 1000 * (time.time() - start_time)
        self.remaining_ms = remaining_ms
        if remaining_ms > 0:
            if not self.paused:
                self.root.after(50, self._arc_countdown, remaining, total_ms, start_time)
                elapsed = total_ms - remaining_ms
                angle = (elapsed / total_ms) * 360
                self.canvas.itemconfigure(self.arc, extent=angle)

        else:
            if not self.paused and self.phase_callback:
                cb = self.phase_callback
                self.phase_callback = None
                cb()

    def pause_exercise(self):
        # halt any pending phase and reset to first rep
        self.paused = True
        self.current_repeat = 0
        self.after_last_repeat = False

        # update UI
        self.show_image(rest_image)
        self.show_next_image(self.movement_images[self.current_index])
        self.index_label.config(text=f"Press resume to restart movement {self.current_index + 1}")
        self.time_label.config(text="")

        self.pause_button.pack_forget()
        self.resume_button.pack(pady=10)
        self.stop_button.pack(pady=40)

        # start flushing EMG buffer while paused
        self.start_flush_loop()

    def resume_exercise(self):
        if not self.paused:
            return
        self.paused = False

        # restore buttons
        self.resume_button.pack_forget()
        self.stop_button.pack_forget()
        self.pause_button.pack(pady=10)

        # restart this movement from rep 1
        self.current_repeat = 0
        self.run_cycle()

    def start_flush_loop(self):
        if self.paused:
            self.recorder.receive_and_ignore(0.1, no_print=True)
            self.root.after(100, self.start_flush_loop)

    def rest_after_movement(self):
        self.current_repeat += 1
        self.show_image(rest_image)
        self.show_next_image(self.movement_images[self.current_index])
        self.index_label.config(
            text=f"Resting between repeats for movement {self.index_offset + self.current_index + 1}"
        )
        self.start_phase(int(self.rest_time * 1000), self.start_movement)

    def stop_session(self):
        self.recorder.finish()
        self.root.destroy()

    def end_session(self):
        self.recorder.finish()
        self.index_label.config(text="Session Complete")
        self.time_label.config(text="")
        total_seconds = int(time.time() - self.start_time)
        self.runtime_label.config(text=f"Total Runtime: {total_seconds} seconds")
        self.pause_button.config(text="Close", command=self.stop_session,
                                 fg="white", bg="black")
        self.resume_button.pack_forget()
        self.stop_button.pack_forget()
        self.pause_button.pack(pady=10)

    def record_emg(self):
        mov_num = self.index_offset + self.current_index + 1
        rep_num = self.current_repeat + 1
        self.recorder.emg_recording(self.perform_time, self.rest_time, mov_num, rep_num)

    def record_rest_before_movement(self):
        mov_num = self.index_offset + self.current_index + 1
        self.recorder.record_initial_rest(self.movement_delay, mov_num, self.perform_time)

if __name__ == "__main__":
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()
