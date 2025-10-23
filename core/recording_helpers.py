# core/recording_helpers.py
from __future__ import annotations

class RecordingController:
    """
    Thin pass-through wrapper around the recorder instance.
    This is wired in without changing behaviour: every method simply forwards
    to the underlying recorder. You can extend this later (retry, logging, etc.)
    without touching the UI.
    """

    def __init__(self, recorder):
        self._rec = recorder

    # ---- direct pass-throughs (same signatures/semantics) ----
    def make_subject_directory(self, subject_id, exercise_set=None):
        return self._rec.make_subject_directory(subject_id, exercise_set=exercise_set)

    def set_id(self, subject_id):
        return self._rec.set_id(subject_id)

    def finish(self):
        return self._rec.finish()

    def receive_and_ignore(self, duration, no_print=False):
        return self._rec.receive_and_ignore(duration, no_print=no_print)

    def get_record(self, duration):
        return self._rec.get_record(duration)

    def record_initial_rest(self, rest_time, movement, perform_time):
        return self._rec.record_initial_rest(rest_time, movement, perform_time)

    def emg_recording(self, perform_time, rest_time, movement, rep):
        return self._rec.emg_recording(perform_time, rest_time, movement, rep)

    def finish_safe(self):
        try:
            self._rec.finish()
        except Exception as e:
            print(f"[RecordingController.finish_safe] {e}")
