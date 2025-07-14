import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
from recording import EmgSession

# Window dimensions for both parameter and main screens
SIZE = 100
WINDOW_WIDTH = 10 * SIZE
WINDOW_HEIGHT = 6 * SIZE

# Movement image lists for sets A and B
movement_images_A = [
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
movement_images_B = [
    "movement_library/EB/Thrumb_up_M13.png",
    "movement_library/EB/Extension_of_index_and_middle_M14.PNG.png",
    "movement_library/EB/Flexion_of_little_and_ring_M15.PNG.png",
    "movement_library/EB/Thumb_opposing_of base_of_little_finger_M16.PNG.png",
    "movement_library/EB/hands_open_M17.PNG.png",
    "movement_library/EB/Fingures_fixed_together_in_fist_M18.PNG.png",
    "movement_library/EB/pointing_index_M19.PNG.png",
    "movement_library/EB/adduction_of_extended_fingers_M20.PNG.png",
    "movement_library/EB/wrist_supination_middile_finger_M21.PNG.png",
    "movement_library/EB/wrist_pronation_M22.PNG.png",
    "movement_library/EB/wrist_supination_little_finger_M23.PNG.png",
    "movement_library/EB/wrist_pronation_little_finger_M24.PNG.png",
    "movement_library/EB/wrist_flexion_M25.PNG.png",
    "movement_library/EB/wrist_extension_M26.PNG.png",
    "movement_library/EB/wrist_radial_deviation_M27.PNG.png",
    "movement_library/EB/wrist_ular_deviation_M28.PNG.png",
    "movement_library/EB/wrist_extension_with_closed_hand_M29.PNG.png"
]

# Rest image filename
rest_image = "movement_library/Rest_M0.png"

class ExerciseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Exercise Timer")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)

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

        # Prepare EMG recorder and flush buffer
        #self.recorder = EmgSession()
        #threading.Thread(target=self._initial_flush_loop, daemon=True).start()

        # Show param screen
        self._build_parameter_screen()

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

        # Exercise set selection
        tk.Label(frame, text="Exercise Set (A, B, AB):", font=("Helvetica",14)).grid(row=6, column=0, sticky='e', padx=20, pady=10)
        combo = ttk.Combobox(frame, textvariable=self.exercise_set_var, font=("Helvetica",14), values=["A","B","AB"], state='readonly')
        combo.grid(row=6, column=1, sticky='w', padx=20, pady=10)
        combo.bind('<<ComboboxSelected>>', lambda e: self._validate_entries())
        self.exercise_set_combobox = combo

        btn = tk.Button(frame, text="Start Session", font=("Helvetica",16), state='disabled', command=self._start_session)
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
            self.movement_images = movement_images_A
            self.index_offset = 0
        elif self.exercise_set == 'B':
            self.movement_images = movement_images_B
            self.index_offset = 12
        else:
            self.movement_images = movement_images_A + movement_images_B
            self.index_offset = 0
        # Setup recorder
        #self.recorder.make_subject_directory(self.subject_id, exercise_set=self.exercise_set)
        #self.recorder.set_id(self.subject_id)
        self.session_started = True
        # Switch to main UI
        self.param_frame.destroy()
        self._build_main_ui()
        self.update_time(int(self.movement_delay * 1000))
        self.run_cycle()

    def _build_main_ui(self):
        self.current_index = 0
        self.current_repeat = 0
        self.after_last_repeat = False
        self.paused = False
        self.start_time = None

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

        # Progress bar
        self.progress = ttk.Progressbar(right,
                                        orient='horizontal',
                                        length=int(WINDOW_WIDTH * 0.6),
                                        mode='determinate')
        self.progress.pack(pady=10)

        self.index_label = tk.Label(right, text="", font=("Helvetica",16))
        self.index_label.pack(pady=10)

        self.pause_button = tk.Button(right, text="Pause", font=("Helvetica",16), fg="black", bg="red", command=self.stop_exercise)
        self.pause_button.pack(pady=10)
        self.resume_button = tk.Button(right, text="Resume", font=("Helvetica",16), fg="black", bg="green", command=self.resume_exercise)
        self.stop_button = tk.Button(right, text="Stop Session", font=("Helvetica",16), fg="white", bg="black", command=self.stop_session)

    def get_variables_text(self):
        return (f"Subject ID: {self.subject_id}\n"
                f"Set: {self.exercise_set}\n"
                f"Perform Time: {(self.perform_time*1000):.0f} ms\n"
                f"Rest Time: {(self.rest_time*1000):.0f} ms\n"
                f"Repeats: {self.num_repeats}\n"
                f"Movement Delay: {(self.movement_delay*1000):.0f} ms")

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
            if self.current_repeat == 0 and not self.after_last_repeat:
                remainder = int(self.movement_delay * 1000)
                self.progress['maximum'] = remainder
                self.progress['value'] = 0
                self.countdown(remainder, self.start_movement)
                self.show_image(rest_image)
                self.show_next_image(self.movement_images[self.current_index])
            elif self.after_last_repeat:
                self.after_last_repeat = False
                self.current_repeat = 0
                self.current_index += 1
                self.run_cycle()
            else:
                self.start_movement()
        else:
            self.show_image(rest_image)
            self.show_next_image(self.movement_images[-1])
            self.index_label.config(text="Session Complete")
            self.update_time(int(self.movement_delay * 1000))
            self.countdown(int(self.movement_delay * 1000), self.end_session)

    def start_movement(self):
        if self.current_repeat < self.num_repeats:
            self.show_image(self.movement_images[self.current_index])
            self.update_index(self.current_index, self.current_repeat)
            self.show_next_image(self.movement_images[self.current_index])
            duration = int(self.perform_time * 1000)
            self.progress['maximum'] = duration
            self.progress['value'] = 0
            self.update_time(duration)
            self.countdown(duration, self.rest_after_movement)
        else:
            self.current_repeat = 0
            self.current_index += 1
            self.run_cycle()

    def rest_after_movement(self):

        self.current_repeat += 1
        self.show_image(rest_image)
        self.show_next_image(self.movement_images[self.current_index])
        self.index_label.config(text=f"Resting between repeats for movement {self.index_offset + self.current_index + 1}")
        duration = int(self.rest_time * 1000)
        self.progress['maximum'] = duration
        self.progress['value'] = 0
        self.update_time(duration)
        self.countdown(duration, self.start_movement)

    def countdown(self, remaining_ms, callback):
        if remaining_ms > 0 and not self.paused:
            # advance progress bar every 50 ms
            self.progress['value'] += 50
            self.root.after(50, self.countdown, remaining_ms - 50, callback)
        else:
            callback()

    def stop_exercise(self):
        self.paused = True
        self.current_repeat = 0
        self.after_last_repeat = False
        self.show_image(rest_image)
        self.show_next_image(self.movement_images[self.current_index])
        self.index_label.config(text="Press Resume or Stop Session")
        self.time_label.config(text="")
        self.pause_button.pack_forget()
        self.resume_button.pack(pady=10)
        self.stop_button.pack(pady=10)
        self.countdown_resume(int(self.movement_delay))
        self.start_flush_loop()

    def countdown_resume(self, seconds):
        if seconds > 0:
            self.resume_button.config(text=f"Resume ({seconds}s)", bg="gray")
            self.resume_button.config(state='disabled')
            self.root.after(1000, self.countdown_resume, seconds-1)
        else:
            self.resume_button.config(state='normal', text="Resume", bg="green")

    def resume_exercise(self):
        if self.paused:
            self.paused = False
            self.resume_button.pack_forget()
            self.stop_button.pack_forget()
            self.pause_button.pack(pady=10)
            self.show_image(rest_image)
            self.show_next_image(self.movement_images[self.current_index])
            self.index_label.config(text=f"Resting before movement {self.index_offset + self.current_index + 1}")
            self.time_label.config(text="")

    def stop_session(self):
        #self.recorder.finish()
        self.root.destroy()

    def end_session(self):
        #self.recorder.finish()
        self.index_label.config(text="Session Complete")
        self.time_label.config(text="")
        self.runtime_label.config(text=f"Total Runtime: {int(time.time() - self.start_time)} seconds")
        self.pause_button.config(text="Close", command=self.stop_session, fg="white", bg="black")
        self.resume_button.pack_forget()
        self.stop_button.pack_forget()
        self.pause_button.pack(pady=10)

    def start_flush_loop(self):
        if self.paused:
            self.root.after(100, self.start_flush_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()
