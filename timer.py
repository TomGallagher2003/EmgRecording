"""
Session GUI for managing EMG/EEG exercise recordings.

This module defines a Tkinter-based application (`ExerciseApp`) that:
- Collects session parameters (subject ID, durations, repeats, set A/B/AB).
- Orchestrates movement/rest prompts with images and timers.
- Controls a backend `Session` recorder (EMG/EEG), including quick device checks,
  buffer flushing, and safe stop/close behavior.
"""

import time
import tkinter as tk
import threading
from recording import Session
from util.data_validation import validate_data
from util.images import Images
from core.ui.device_screen import build_device_screen
from core.ui.parameter_screen import build_parameter_screen
from core.ui.main_screen import build_main_ui
from core.ui.image_loader import load_scaled_tk

from core.recording_helpers import RecordingController
from experiment_settings import (DATA_DESTINATION_PATH, IMAGE_SOURCE_PATH,
                                 INITIAL_BASELINE_SECONDS, WINDOW_WIDTH, WINDOW_HEIGHT, ARC_TICK_MS)
rest_image = Images.REST

def _now():
    """Return the current monotonic time in seconds."""
    return time.monotonic()


class ExerciseApp:
    """Tkinter UI to guide and record EMG/EEG exercise sessions."""

    def __init__(self, root):
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

        # Recorder instance & controller (set after device confirmation)
        self.recorder = None
        self.rec = None  # type: ignore

        # Show device selection screen first
        build_device_screen(self, WINDOW_WIDTH, WINDOW_HEIGHT)

    # ---------------- Device selection ----------------

    def _validate_device_selection(self):
        """Enable or disable the continue button based on selection state."""
        enabled = self.emg_var.get() or self.eeg_var.get()
        self.device_continue_btn.config(state='normal' if enabled else 'disabled')
        self.device_error.config(text="" if enabled else "Please select at least one device (EEG and/or EMG).")

    def _confirm_devices(self):
        """Persist device selections, run quick device check, and proceed."""
        # Save selections
        self.use_emg = self.emg_var.get()
        self.use_eeg = self.eeg_var.get()

        # Lock UI while checking
        self.device_continue_btn.config(state='disabled')
        self.device_error.config(text="Checking devices...")
        self.root.update_idletasks()

        try:
            # Create recording session now
            self.recorder = Session(self.use_emg, self.use_eeg, DATA_DESTINATION_PATH)
            self.rec = RecordingController(self.recorder)  # <-- wire controller

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
        build_parameter_screen(self, WINDOW_WIDTH, WINDOW_HEIGHT)

    def quick_device_check(self):
        """Run a short connectivity and data sanity check."""
        try:
            self.rec.receive_and_ignore(2.0)
            test_data = self.rec.get_record(0.1)
            return bool(validate_data(test_data, self.use_emg, self.use_eeg))
        except Exception as e:
            print(f"[validate_data] Caught exception: {e!r}")
            print(f"Type: {type(e).__name__}")
        return False

    def _initial_flush_loop(self):
        """Continuously flush device buffers until the session formally starts."""
        time.sleep(0.2)
        while not self.session_started:
            self.rec.receive_and_ignore(0.1, no_print=True)
            time.sleep(0.1)

    # ---------------- Parameter screen ----------------

    def _validate_entries(self):
        """Validate form inputs and enable the Start button if all are valid."""
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
        """Read parameters, configure images, set up recorder, and start session."""
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

        # Setup recorder (directory/id)
        self.rec.make_subject_directory(self.subject_id, exercise_set=self.exercise_set)
        self.rec.set_id(self.subject_id)
        self.session_started = True

        # Switch to main UI and begin
        self.param_frame.destroy()
        build_main_ui(self, WINDOW_WIDTH, WINDOW_HEIGHT, arc_tick_ms=50)
        self.run_cycle()

    # ---------------- Main UI helpers ----------------

    def get_variables_text(self):
        """Return a multi-line summary of the current session parameters."""
        return (f"Subject ID: {self.subject_id}\n"
                f"Set: {self.exercise_set}\n"
                f"Perform Time: {self.perform_time*1000:.0f} ms\n"
                f"Rest Time : {self.rest_time*1000:.0f} ms\n"
                f"Repeats: {self.num_repeats}")

    def show_image(self, path):
        """Display the main (current) image scaled to fit the right panel."""
        max_w = int(WINDOW_WIDTH * 0.7 * 1.3)
        max_h = int(WINDOW_HEIGHT // 2.3 * 1.3)
        tkimg = load_scaled_tk(path, max_w, max_h)
        self.image_label.config(image=tkimg)
        self.image_label.image = tkimg

    def show_next_image(self, path):
        """Display the upcoming (next) image preview on the left panel."""
        max_w = int(WINDOW_WIDTH * 0.7 // 1.5 * 1.2)
        max_h = int(WINDOW_HEIGHT // 2.3 // 1.5 * 1.2)
        tkimg = load_scaled_tk(path, max_w, max_h)
        self.next_image_label.config(image=tkimg)
        self.next_image_label.image = tkimg

    def update_index(self, mov, rep):
        """Update the movement/repetition label."""
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
        """Advance the session state machine."""
        if self.start_time is None:
            self.start_time = _now()
            self.update_runtime()

        if self.current_index < len(self.movement_images):
            # Pre-movement rest before the first rep of a movement
            if self.current_repeat == 0 and not self.after_last_repeat:
                pre_rest_sec = INITIAL_BASELINE_SECONDS if self.current_index == 0 else self.rest_time
                remainder = int(pre_rest_sec * 1000)

                self.index_label.config(text=f"Resting before movement {self.current_index + 1}")

                self.show_image(rest_image)
                self.show_next_image(self.movement_images[self.current_index])
                self.next_image_label.config(highlightthickness=2, highlightbackground="red")

                # RECORD ONLY the very first baseline (movement 1)
                if not self.paused and self.current_index == 0:
                    threading.Thread(
                        target=self.rec.record_initial_rest,
                        args=(INITIAL_BASELINE_SECONDS,
                              self.index_offset + 1,
                              self.perform_time),
                        daemon=True, name="baseline_rest"
                    ).start()

                # RED for rest; label shows TOTAL phase time (no ticking)
                self.start_phase(remainder, self.start_movement, color="red")

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
            self.next_image_label.config(highlightthickness=0)
            self.index_label.config(text="Session Complete")
            self.start_phase(int(self.rest_time * 1000), self.end_session, color="red")

    # ---------------- Movement phases ----------------

    def start_movement(self):
        """Start (or continue) the movement phase for the current movement."""
        self.next_image_label.config(highlightthickness=0)

        if self.current_repeat < self.num_repeats:
            self.show_image(self.movement_images[self.current_index])
            self.update_index(self.current_index, self.current_repeat)
            if not self.paused:
                mov_num = self.index_offset + self.current_index + 1
                rep_num = self.current_repeat + 1
                threading.Thread(
                    target=self.rec.emg_recording,
                    args=(self.perform_time, self.rest_time, mov_num, rep_num),
                    daemon=True,
                    name="emg_rep",
                ).start()
            self.show_next_image(self.movement_images[self.current_index])

            self.start_phase(int(self.perform_time * 1000), self._after_movement_phase, color="green")
        else:
            self.current_repeat = 0
            self.current_index += 1
            self.run_cycle()

    def _after_movement_phase(self):
        """Handle the end of a movement phase."""
        if (self.current_repeat + 1) < self.num_repeats:
            self.rest_after_movement()
        else:
            self.current_repeat = 0
            self.after_last_repeat = True
            self.run_cycle()

    # ---------------- Timer (radial arc) ----------------

    def start_phase(self, duration_ms, callback, color="black"):
        """Begin a timed phase with a radial countdown arc and completion callback."""
        # Reset arc and apply requested color
        try:
            self.canvas.itemconfigure(self.arc, extent=0, outline=color)
        except Exception:
            # Canvas might be gone if window closing; safe to ignore
            return

        self.phase_callback = callback
        self.total_ms = max(1, int(duration_ms))
        self.remaining_ms = int(duration_ms)

        # Fixed label (no ticking)
        self.time_label.config(text=f"Time: {self.total_ms / 1000:.1f} s")

        # Delegate to PhaseManager (wired in main screen)
        if hasattr(self, "phase") and self.phase:
            self.phase.start(
                duration_ms=self.total_ms,
                on_done=self._on_phase_done,
                color=color,
                state_text="",
            )

    def _on_phase_done(self):
        """Internal bridge so PhaseManager calls the original callback semantics."""
        if not self.paused and self.phase_callback:
            cb = self.phase_callback
            self.phase_callback = None
            cb()

    # ---------------- Pause/Resume/Stop ----------------

    def pause_exercise(self):
        """Pause the session and reset the current movement to repetition 1."""
        self.paused = True
        self.current_repeat = 0
        self.after_last_repeat = False

        self.show_image(rest_image)
        self.show_next_image(self.movement_images[self.current_index])
        self.next_image_label.config(highlightthickness=0)
        self.index_label.config(text=f"Press resume to restart movement {self.current_index + 1}")
        self.time_label.config(text="")

        self.pause_button.pack_forget()
        self.resume_button.pack(pady=10)
        self.stop_button.pack(pady=40)

        if hasattr(self, "phase") and self.phase:
            self.phase.pause()

        self.start_flush_loop()

    def resume_exercise(self):
        """Resume the session from a paused state."""
        if not self.paused:
            return
        self.paused = False

        self.resume_button.pack_forget()
        self.stop_button.pack_forget()
        self.pause_button.pack(pady=10)

        if hasattr(self, "phase") and self.phase:
            self.phase.resume()

        self.current_repeat = 0
        self.run_cycle()

    def start_flush_loop(self):
        """Continuously flush the device socket while paused."""
        if self.paused:
            self.rec.receive_and_ignore(0.1, no_print=True)
            self.root.after(100, self.start_flush_loop)

    def rest_after_movement(self):
        """Handle the inter-repetition rest (UI-only) for the current movement."""
        self.current_repeat += 1
        self.show_image(rest_image)
        self.show_next_image(self.movement_images[self.current_index])
        self.next_image_label.config(highlightthickness=0)
        self.index_label.config(
            text=f"Resting between repeats for movement {self.index_offset + self.current_index + 1}"
        )
        self.start_phase(int(self.rest_time * 1000), self.start_movement, color="red")

    def stop_session(self):
        """Idempotent stop: safe on double-click; always attempts recorder.finish() once."""
        if getattr(self, "_stopped", False):
            return
        self._stopped = True

        # Stop phase callbacks
        try:
            if hasattr(self, "phase") and self.phase:
                self.phase.stop()
        except Exception:
            pass

        try:
            self.rec.finish()
        except Exception as e:
            print(f"[stop_session] finish error: {e}")


    def end_session(self):
        """Finalize the session after all movements are complete."""
        try:
            self.rec.finish()
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


# Launch the Tkinter UI and start the ExerciseApp event loop.
if __name__ == "__main__":
    root = tk.Tk()
    app = ExerciseApp(root)
    root.mainloop()
