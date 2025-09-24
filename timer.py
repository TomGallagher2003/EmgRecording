"""
Session GUI for managing EMG/EEG exercise recordings.

This module defines a Tkinter-based application (`ExerciseApp`) that:
- Collects session parameters (subject ID, durations, repeats, set A/B/AB).
- Orchestrates movement/rest prompts with images and timers.
- Controls a backend `Session` recorder (EMG/EEG), including quick device checks,
  buffer flushing, and safe stop/close behavior.

The UI presents three screens:
1. Device selection (EMG/EEG) with a quick validation check.
2. Parameter entry.
3. Main run screen with countdowns and progress indicators.

Recording flow (as configured):
- Only the very first pre-movement rest (fixed 5 seconds) is recorded, and is
  attributed to movement 1.
- All later pre-movement rests are UI-only (not recorded).
- Movement recordings are performed through `Session.emg_recording`, which
  captures the contraction plus the trailing inter-repetition rest.
"""

import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
from recording import Session
from util.data_validation import validate_data
from util.images import Images

# Window dimensions for both parameter and main screens
SIZE = 135
WINDOW_WIDTH = 10 * SIZE
WINDOW_HEIGHT = 5 * SIZE

# Rest image filename
rest_image = Images.REST

# Fixed initial baseline (before the very first movement) — recorded under movement 1
INITIAL_BASELINE_SECONDS = 4


def _now():
    """Return the current monotonic time in seconds.

    Using a monotonic clock prevents drift and is robust to system time changes.

    Returns:
        float: Current monotonic time (seconds).
    """
    return time.monotonic()


class ExerciseApp:
    """Tkinter UI to guide and record EMG/EEG exercise sessions.

    The flow includes:
    * Device selection and validation.
    * Session parameter entry.
    * Guided execution of movements with rest phases and countdown arcs.

    Recording rules:
    * Only the very first baseline rest (5 seconds) is recorded (movement 1).
    * All later pre-movement rests are UI-only (not recorded).
    * Movement recording is handled via `Session.emg_recording`, which records
      contraction plus trailing inter-rep rest.

    Attributes:
        root (tk.Tk): Root Tkinter window.
        use_emg (bool): Whether EMG device is selected.
        use_eeg (bool): Whether EEG device is selected.
        session_started (bool): Whether the session has started.
        subject_id (int | None): Subject identifier.
        perform_time (float | None): Movement/contraction duration (seconds).
        rest_time (float | None): Inter-repetition rest duration (seconds). Also used as between-movement rest in the UI.
        num_repeats (int | None): Number of repetitions per movement.
        exercise_set (str | None): Exercise set label ('A', 'B', or 'AB').
        exercise_set_var (tk.StringVar): Backing variable for the set combobox.
        movement_images (list[str]): File paths of movement images for the session.
        index_offset (int): Offset for numbering movements (A=0, B=12, AB=0).
        paused (bool): Whether the session is paused.
        remaining_ms (int): Remaining milliseconds in the current phase.
        total_ms (int): Total milliseconds of the current phase.
        phase_callback (callable | None): Callback invoked at end of a phase.
        _countdown_job (str | None): Tk `after` job id for the countdown loop.
        recorder (Session | None): Recorder instance (created after device confirmation).

        device_frame (tk.Frame): Device selection frame.
        param_frame (tk.Frame): Parameter entry frame.
        left_frame (tk.Frame): Left panel of main screen.
        right_frame (tk.Frame): Right panel of main screen.
        next_image_label (tk.Label): Preview (next movement) image label.
        variable_label (tk.Label): Label showing the session parameters summary.
        runtime_label (tk.Label): Total runtime label.
        image_label (tk.Label): Main (current movement) image label.
        time_label (tk.Label): Phase time label (fixed per-phase, not ticking).
        index_label (tk.Label): Movement and repeat index label.
        canvas (tk.Canvas): Radial countdown canvas.
        arc (int): Canvas arc item id for radial progress.
        pause_button (tk.Button): Pause button.
        resume_button (tk.Button): Resume button.
        stop_button (tk.Button): Stop session button.

        # Runtime state:
        current_index (int): Zero-based index into `movement_images`.
        current_repeat (int): Zero-based repetition index for the current movement.
        after_last_repeat (bool): Whether the last movement phase ended the final rep.
        start_time (float | None): Monotonic timestamp of session start.
        prev (float): Last monotonic timestamp used for internal timing (reserved).
    """

    def __init__(self, root):
        """Initialize the exercise app and show device selection.

        Args:
            root (tk.Tk): Root Tkinter window.
        """
        self.root = root
        self.root.title("Exercise Timer")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+80+40")
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
        self.exercise_set = None
        self.exercise_set_var = tk.StringVar()
        self.movement_images = []
        self.index_offset = 0

        # Pause/resume state
        self.paused = False
        self.remaining_ms = 0
        self.total_ms = 0
        self.phase_callback = None
        self._countdown_job = None

        # Recorder instance (set after device confirmation)
        self.recorder = None

        # Show device selection screen first
        self._build_device_screen()

    # ---------------- Device selection ----------------

    def _build_device_screen(self):
        """Build and render the device selection screen.

        Layout:
            - EMG/EEG checkboxes.
            - Validation error label.
            - Continue button (enabled if at least one device is checked).
        """
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
        """Enable or disable the continue button based on selection state.

        Enables the Continue button if either EMG or EEG is checked; otherwise
        disables it and shows an error message.
        """
        enabled = self.emg_var.get() or self.eeg_var.get()
        self.device_continue_btn.config(state='normal' if enabled else 'disabled')
        self.device_error.config(text="" if enabled else "Please select at least one device (EEG and/or EMG).")

    def _confirm_devices(self):
        """Persist device selections, run quick device check, and proceed.

        Creates the recorder instance and attempts a short data validation read.
        On failure, the app displays an error and closes. On success, the UI
        advances to the parameter screen while a small background flush loop
        keeps buffers clean until the session starts.
        """
        # Save selections
        self.use_emg = self.emg_var.get()
        self.use_eeg = self.eeg_var.get()

        # Lock UI while checking
        self.device_continue_btn.config(state='disabled')
        self.device_error.config(text="Checking devices...")
        self.root.update_idletasks()

        try:
            # Create recording session now
            self.recorder = Session(self.use_emg, self.use_eeg)

            # Do quick data check before proceeding
            if not self.quick_device_check():
                self.device_error.config(
                    text=("Device check failed. Reboot the Syncstation and ensure the selected devices are connected.\n"
                          "The software will now close")
                )
                self.root.after(2500, self.stop_session)
                return
        except Exception as e:
            self.device_error.config(text=f"Failed to initialize devices: {e}")
            self.root.after(2500, self.stop_session)
            return

        # Start initial flush loop after recorder exists
        threading.Thread(target=self._initial_flush_loop, daemon=True).start()

        # Proceed to parameter screen
        self.device_frame.destroy()
        self._build_parameter_screen()

    def quick_device_check(self):
        """Run a short connectivity and data sanity check.

        Returns:
            bool: True if a brief read succeeds and the resulting data shape/content
                passes `validate_data`; False otherwise.
        """
        try:
            self.recorder.receive_and_ignore(2.0)
            test_data = self.recorder.get_record(0.1)
            return bool(validate_data(test_data, self.use_emg, self.use_eeg))
        except Exception as e:
            print(f"[validate_data] Caught exception: {e!r}")
            print(f"Type: {type(e).__name__}")
        return False

    def _initial_flush_loop(self):
        """Continuously flush device buffers until the session formally starts.

        This runs in a daemon thread so the UI stays responsive; it repeatedly
        calls `receive_and_ignore` to keep the incoming stream clean.

        Note:
            This is a small periodic flush before the session begins.
        """
        time.sleep(0.2)
        while not self.session_started:
            self.recorder.receive_and_ignore(0.1, no_print=True)
            time.sleep(0.1)

    # ---------------- Parameter screen ----------------

    def _build_parameter_screen(self):
        """Render the parameter entry form (subject, durations, repeats, set)."""
        frame = tk.Frame(self.root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        frame.pack(fill='both', expand=True)
        self.param_frame = frame
        for r in (0, 8):
            frame.grid_rowconfigure(r, weight=1)
        for c in (0, 1):
            frame.grid_columnconfigure(c, weight=1)

        labels = [
            "Subject ID:",
            "Perform Time (seconds):",
            "Rest Time Between Repetitions (seconds):",
            "Number of Repetitions:",
        ]
        self.entries = []
        for i, text in enumerate(labels, start=1):
            tk.Label(frame, text=text, font=("Helvetica", 14)).grid(row=i, column=0, sticky='e', padx=20, pady=10)
            entry = tk.Entry(frame, font=("Helvetica", 14))
            entry.grid(row=i, column=1, sticky='w', padx=20, pady=10)
            entry.bind('<KeyRelease>', lambda _e: self._validate_entries())
            self.entries.append(entry)

        (self.subject_id_entry,
         self.perform_time_entry,
         self.rest_time_entry,
         self.num_repeats_entry) = self.entries

        tk.Label(frame, text="Exercise Set (A, B, AB):", font=("Helvetica", 14)) \
            .grid(row=6, column=0, sticky='e', padx=20, pady=10)
        combo = ttk.Combobox(frame, textvariable=self.exercise_set_var, font=("Helvetica", 14),
                             values=["A", "B", "AB"], state='readonly')
        combo.grid(row=6, column=1, sticky='w', padx=20, pady=10)
        combo.bind('<<ComboboxSelected>>', lambda _e: self._validate_entries())
        self.exercise_set_combobox = combo

        btn = tk.Button(frame, text="Start Session", font=("Helvetica", 16),
                        state='disabled', command=self._start_session)
        btn.grid(row=7, column=0, columnspan=2, pady=30)
        self.start_button = btn

    def _validate_entries(self):
        """Validate form inputs and enable the Start button if all are valid.

        Validations:
            * Subject ID must be a non-negative integer.
            * Perform/rest times must be positive floats.
            * Repeats must be a positive integer.
            * Exercise set must be one of A/B/AB.
        """
        try:
            sid = int(self.subject_id_entry.get().strip())
            if sid < 0:
                raise ValueError
            perf = float(self.perform_time_entry.get().strip())
            rrest = float(self.rest_time_entry.get().strip())
            reps = int(self.num_repeats_entry.get().strip())
            eset = self.exercise_set_var.get()
            ok = (perf > 0 and rrest > 0 and reps > 0 and eset in ("A", "B", "AB"))
        except Exception:
            ok = False
        self.start_button.config(state='normal' if ok else 'disabled')

    def _start_session(self):
        """Read parameters, configure images, set up recorder, and start session.

        Side Effects:
            - Creates subject directory and assigns the subject ID to the recorder.
            - Destroys the parameter frame and builds the main UI.
            - Starts the main run cycle.
        """
        # Read params
        self.subject_id = int(self.subject_id_entry.get().strip())
        self.perform_time = float(self.perform_time_entry.get())
        self.rest_time = float(self.rest_time_entry.get())  # inter-rep; also used as between-movement rest (UI-only)
        self.num_repeats = int(self.num_repeats_entry.get())
        self.exercise_set = self.exercise_set_var.get()

        # Configure movement list
        if self.exercise_set == 'A':
            self.movement_images = list(Images.MOVEMENT_IMAGES_A)
            self.index_offset = 0
        elif self.exercise_set == 'B':
            self.movement_images = list(Images.MOVEMENT_IMAGES_B)
            self.index_offset = 12
        else:
            self.movement_images = list(Images.MOVEMENT_IMAGES_A) + list(Images.MOVEMENT_IMAGES_B)
            self.index_offset = 0

        # Setup recorder (directory/id) — recorder already exists
        self.recorder.make_subject_directory(self.subject_id, exercise_set=self.exercise_set)
        self.recorder.set_id(self.subject_id)
        self.session_started = True

        # Switch to main UI and begin
        self.param_frame.destroy()
        self._build_main_ui()
        self.run_cycle()

    # ---------------- Main UI ----------------

    def _build_main_ui(self):
        """Build the main run UI (current/next image, countdown, controls)."""
        self.current_index = 0
        self.current_repeat = 0
        self.after_last_repeat = False
        self.start_time = None
        self.prev = _now()

        left = tk.Frame(self.root, width=WINDOW_WIDTH // 2, height=WINDOW_HEIGHT)
        left.pack(side='left', fill='both', pady=50, padx=30)
        right = tk.Frame(self.root, width=WINDOW_WIDTH // 2, height=WINDOW_HEIGHT + 30)
        right.pack(side='right', fill='both', pady=20)
        self.left_frame, self.right_frame = left, right

        self.next_image_label = tk.Label(left, highlightthickness=0)  # toggled red border in pre-rest
        self.next_image_label.pack(anchor='n', padx=10, pady=10)
        self.variable_label = tk.Label(left, text=self.get_variables_text(), font=("Helvetica", 14))
        self.variable_label.pack(anchor='n', padx=10, pady=10)
        self.runtime_label = tk.Label(left, text="Runtime: 0 s", font=("Helvetica", 16))
        self.runtime_label.pack(anchor='n', padx=10, pady=10)

        self.image_label = tk.Label(right)
        self.image_label.pack(pady=10, padx=WINDOW_WIDTH * 0.1)

        self.time_label = tk.Label(right, text="", font=("Helvetica", 16))
        self.time_label.pack(pady=10)
        self.index_label = tk.Label(right, text="", font=("Helvetica", 16))
        self.index_label.pack(pady=10)

        # Radial countdown indicator
        self.canvas = tk.Canvas(self.right_frame, width=60, height=80)
        self.canvas.pack(pady=10)
        self.canvas.create_oval(12, 12, 50, 50, outline='#ddd', width=8)
        self.arc = self.canvas.create_arc(12, 12, 50, 50, start=90, extent=0,
                                          style='arc', width=8)

        self.pause_button = tk.Button(left, text="Pause", font=("Helvetica", 16),
                                      fg="black", bg="red", command=self.pause_exercise)
        self.pause_button.pack(pady=10)

        self.resume_button = tk.Button(left, text="Resume", font=("Helvetica", 16),
                                       fg="black", bg="green", command=self.resume_exercise)
        self.stop_button = tk.Button(left, text="Stop Session", font=("Helvetica", 16),
                                     fg="white", bg="black", command=self.stop_session)

    def get_variables_text(self):
        """Return a multi-line summary of the current session parameters.

        Returns:
            str: Human-readable summary, including subject, set, durations, and repeats.
        """
        return (f"Subject ID: {self.subject_id}\n"
                f"Set: {self.exercise_set}\n"
                f"Perform Time: {self.perform_time*1000:.0f} ms\n"
                f"Rest Time : {self.rest_time*1000:.0f} ms\n"
                f"Repeats: {self.num_repeats}")

    def show_image(self, path):
        """Display the main (current) image scaled to fit the right panel.

        Args:
            path (str): Filesystem path to the image to display.
        """
        img = Image.open(path)
        max_w = WINDOW_WIDTH * 0.7 * 1.3
        max_h = WINDOW_HEIGHT // 2.3 * 1.3
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self.image_label.config(image=tkimg)
        self.image_label.image = tkimg

    def show_next_image(self, path):
        """Display the upcoming (next) image preview on the left panel.

        Args:
            path (str): Filesystem path to the image to preview.
        """
        img = Image.open(path)
        max_w = WINDOW_WIDTH * 0.7 // 1.5 * 1.2
        max_h = WINDOW_HEIGHT // 2.3 // 1.5 * 1.2
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self.next_image_label.config(image=tkimg)
        self.next_image_label.image = tkimg

    def update_time(self, remaining_ms):
        """Update the phase time label.

        Note:
            This app shows the total phase time (fixed per phase) and does not
            tick down. The label is updated by `start_phase`.

        Args:
            remaining_ms (int | float): Remaining milliseconds (unused for ticking; kept for compatibility).
        """
        self.time_label.config(text=f"Time: {(remaining_ms / 1000):.1f} s")

    def update_index(self, mov, rep):
        """Update the movement/repetition label.

        Args:
            mov (int): Zero-based movement index within the current set.
            rep (int): Zero-based repetition index within the current movement.
        """
        number = self.index_offset + mov + 1
        self.index_label.config(text=f"Movement: {number}, Repeat: {rep + 1}")

    def update_runtime(self):
        """Update the total runtime label once per second while the session runs."""
        if self.start_time is not None:
            elapsed = int((_now() - self.start_time) * 1000)
            self.runtime_label.config(text=f"Runtime: {elapsed // 1000} s")
            self.root.after(1000, self.update_runtime)

    # ---------------- Run cycle ----------------

    def run_cycle(self):
        """Advance the session state machine.

        Handles:
            - Pre-movement rest (UI) before the first repetition of each movement.
            - Movement phase execution and recording.
            - Inter-repetition rest (UI) when repeats remain.
            - Skipping final inter-rep rest (UI) after the last repetition.
            - Transitioning between movements until session completion.
        """
        if self.start_time is None:
            self.start_time = _now()
            self.update_runtime()

        if self.current_index < len(self.movement_images):
            # Pre-movement rest before the first rep of a movement
            if self.current_repeat == 0 and not self.after_last_repeat:
                # duration: 5s if first movement, else rest_time (UI only for later ones)
                pre_rest_sec = INITIAL_BASELINE_SECONDS if self.current_index == 0 else self.rest_time
                remainder = int(pre_rest_sec * 1000)

                self.index_label.config(text=f"Resting before movement {self.current_index + 1}")

                # Show current rest image and NEXT movement preview with red border
                self.show_image(rest_image)
                self.show_next_image(self.movement_images[self.current_index])
                self.next_image_label.config(highlightthickness=2, highlightbackground="red")

                # RECORD ONLY the very first baseline (movement 1)
                if not self.paused and self.current_index == 0:
                    threading.Thread(
                        target=self.recorder.record_initial_rest,
                        args=(INITIAL_BASELINE_SECONDS,
                              self.index_offset + 1,
                              self.perform_time),
                        daemon=True
                    ).start()

                # RED for rest; label shows TOTAL phase time (no ticking)
                self.start_phase(remainder, self.start_movement, color="red")

            # move to next movement after finishing previous one
            elif self.after_last_repeat:
                self.after_last_repeat = False
                self.current_repeat = 0
                self.current_index += 1
                self.run_cycle()

            # continue into movement
            else:
                self.start_movement()
        else:
            # session complete: final rest before closing uses rest_time (UI only)
            self.show_image(rest_image)
            self.show_next_image(self.movement_images[-1])
            self.next_image_label.config(highlightthickness=0)
            self.index_label.config(text="Session Complete")
            self.start_phase(int(self.rest_time * 1000), self.end_session, color="red")

    # ---------------- Movement phases ----------------

    def start_movement(self):
        """Start (or continue) the movement phase for the current movement.

        Behavior:
            - Clears the preview red border (pre-rest visual).
            - Displays the current movement image.
            - Spawns the recording thread for this movement/rep via `record_emg`.
            - Starts a movement-phase timer (green arc); at completion, the flow
              continues in `_after_movement_phase`.
        """
        # Clear the red border during movement
        self.next_image_label.config(highlightthickness=0)

        if self.current_repeat < self.num_repeats:
            self.show_image(self.movement_images[self.current_index])
            self.update_index(self.current_index, self.current_repeat)
            if not self.paused:
                # Recording happens ONLY here: contraction + trailing rest (emg_recording handles both)
                threading.Thread(target=self.record_emg, daemon=True).start()
            self.show_next_image(self.movement_images[self.current_index])

            # GREEN for movement; when it ends, decide whether to rest or advance
            self.start_phase(int(self.perform_time * 1000), self._after_movement_phase, color="green")
        else:
            # Safety: move on if repeats exhausted
            self.current_repeat = 0
            self.current_index += 1
            self.run_cycle()

    def _after_movement_phase(self):
        """Handle the end of a movement phase.

        If more repetitions remain for the current movement, show the inter-rep
        rest (UI-only) and then start the next rep. If the last repetition just
        finished, skip the final inter-rep rest (UI) and advance to the next
        movement's pre-rest.
        """
        if (self.current_repeat + 1) < self.num_repeats:
            self.rest_after_movement()
        else:
            # Last rep: skip inter-rep final rest UI and advance to next movement pre-rest
            self.current_repeat = 0
            self.after_last_repeat = True
            self.run_cycle()

    # ---------------- Timer (radial arc) ----------------

    def start_phase(self, duration_ms, callback, color="black"):
        """Begin a timed phase with a radial countdown arc and completion callback.

        The time label displays the total phase time (fixed) rather than counting
        down. The radial arc animates from 0° to 360° over the phase duration.

        Args:
            duration_ms (int): Phase duration in milliseconds.
            callback (callable): Function to invoke when the phase completes.
            color (str): Outline color for the radial arc (e.g., "red" for rest, "green" for movement).
        """
        # Cancel any prior countdown to avoid overlap
        if self._countdown_job is not None:
            try:
                self.root.after_cancel(self._countdown_job)
            except Exception:
                pass
            self._countdown_job = None

        # Reset arc and apply requested color
        self.canvas.itemconfigure(self.arc, extent=0, outline=color)
        self.phase_callback = callback
        self.total_ms = max(1, int(duration_ms))
        self.remaining_ms = int(duration_ms)

        # Time label shows TOTAL phase time (fixed), not ticking down
        self.time_label.config(text=f"Time: {self.total_ms / 1000:.1f} s")

        # Kick off the countdown loop using monotonic timing (arc animation only)
        self._arc_countdown(self.remaining_ms, self.total_ms, start_time=0)

    def _arc_countdown(self, remaining_ms, total_ms, start_time=0):
        """Internal countdown loop that animates the radial arc.

        Uses monotonic time to compute elapsed and remaining duration. While
        paused, the arc animation is effectively frozen.

        Args:
            remaining_ms (int): Remaining milliseconds from the previous tick.
            total_ms (int): Total duration of the current phase in milliseconds.
            start_time (float): Monotonic start timestamp; if 0, initialized on entry.
        """
        if start_time == 0:
            start_time = _now()

        # If paused, freeze the arc by adjusting a "virtual" start
        if self.paused:
            frozen_start = _now() - (total_ms - remaining_ms) / 1000.0
            self._countdown_job = self.root.after(80, self._arc_countdown, remaining_ms, total_ms, frozen_start)
            return

        elapsed_ms = int((_now() - start_time) * 1000)
        rem = total_ms - elapsed_ms
        if rem < 0:
            rem = 0

        self.remaining_ms = rem

        # Update arc (0..360). Do NOT update the time label here.
        angle = (min(elapsed_ms, total_ms) / total_ms) * 360.0
        self.canvas.itemconfigure(self.arc, extent=angle)

        if rem > 0:
            self._countdown_job = self.root.after(50, self._arc_countdown, rem, total_ms, start_time)
        else:
            if not self.paused and self.phase_callback:
                cb = self.phase_callback
                self.phase_callback = None
                cb()

    # ---------------- Pause/Resume/Stop ----------------

    def pause_exercise(self):
        """Pause the session and reset the current movement to repetition 1.

        UI changes:
            - Shows rest image and preview.
            - Displays resume/stop controls.
            - Keeps device buffer clean via a lightweight periodic flush.
        """
        self.paused = True
        self.current_repeat = 0
        self.after_last_repeat = False

        self.show_image(rest_image)
        # Keep preview and remove any red border when pausing
        self.show_next_image(self.movement_images[self.current_index])
        self.next_image_label.config(highlightthickness=0)
        self.index_label.config(text=f"Press resume to restart movement {self.current_index + 1}")
        self.time_label.config(text="")

        self.pause_button.pack_forget()
        self.resume_button.pack(pady=10)
        self.stop_button.pack(pady=40)

        self.start_flush_loop()

    def resume_exercise(self):
        """Resume the session from a paused state.

        Restores the pause control and re-enters the run cycle at the current
        movement, starting from repetition 1.
        """
        if not self.paused:
            return
        self.paused = False

        self.resume_button.pack_forget()
        self.stop_button.pack_forget()
        self.pause_button.pack(pady=10)

        self.current_repeat = 0
        self.run_cycle()

    def start_flush_loop(self):
        """Continuously flush the device socket while paused.

        Reads and discards small bursts of data at ~10 Hz to prevent stale packets
        from building up on the EMG/EEG stream during a paused UI state.
        """
        if self.paused:
            self.recorder.receive_and_ignore(0.1, no_print=True)
            self.root.after(100, self.start_flush_loop)

    def rest_after_movement(self):
        """Handle the inter-repetition rest (UI-only) for the current movement.

        Increments the repeat counter, shows a rest screen, and schedules the next
        movement phase after the configured inter-rep rest time.
        """
        self.current_repeat += 1
        self.show_image(rest_image)
        self.show_next_image(self.movement_images[self.current_index])
        self.next_image_label.config(highlightthickness=0)
        self.index_label.config(
            text=f"Resting between repeats for movement {self.index_offset + self.current_index + 1}"
        )
        # RED for inter-rep rest UI
        self.start_phase(int(self.rest_time * 1000), self.start_movement, color="red")

    def stop_session(self):
        """Immediately stop the recording session and close the UI.

        Calls `recorder.finish()` and destroys the root window.
        """
        try:
            self.recorder.finish()
        finally:
            self.root.destroy()

    def end_session(self):
        """Finalize the session after all movements are complete.

        Updates the UI to the completed state, shows total runtime, and converts
        the Pause button into a Close action.
        """
        try:
            self.recorder.finish()
        finally:
            self.index_label.config(text="Session Complete")
            self.time_label.config(text="")
            total_seconds = int(_now() - self.start_time) if self.start_time else 0
            self.runtime_label.config(text=f"Total Runtime: {total_seconds} seconds")
            self.pause_button.config(text="Close", command=self.stop_session,
                                     fg="white", bg="black")
            self.resume_button.pack_forget()
            self.stop_button.pack_forget()
            self.pause_button.pack(pady=10)

    # ---------------- Recording hooks ----------------

    def record_emg(self):
        """Spawned worker that records one movement repetition.

        Computes the 1-based movement and repetition indices and invokes the
        underlying `Session.emg_recording`.

        The `Session.emg_recording` call is expected to handle both the
        contraction (perform_time) and the trailing inter-repetition rest (rest_time).

        Raises:
            Any exception from the underlying recording layer will surface in the
            worker thread (logged by Python's threading module).
        """
        mov_num = self.index_offset + self.current_index + 1
        rep_num = self.current_repeat + 1
        # This records perform_time + trailing rest_time internally
        self.recorder.emg_recording(self.perform_time, self.rest_time, mov_num, rep_num)


# Launch the Tkinter UI and start the ExerciseApp event loop.
if __name__ == "__main__":
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()
