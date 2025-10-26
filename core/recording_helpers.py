# core/recording_helpers.py
"""
Recording helpers: thin wrapper around a recorder instance.

This module exposes :class:`RecordingController`, a pass-through façade that
forwards calls to an underlying *recorder* object. It lets you add logging,
metrics, retries, or safety guards later without changing the UI or the recorder
implementation. The class and its methods are documented to be discovered by
**mkdocstrings** for inclusion in your MkDocs site.

Overview
--------
- Decouples the UI from a specific recorder implementation.
- Preserves signatures/semantics by delegating directly to ``self._rec``.
- Provides :meth:`RecordingController.finish_safe` as a guarded variant of ``finish``.

Integration contract
--------------------
The wrapped recorder is expected to implement the following methods with
compatible semantics (this controller forwards to them unchanged):

- ``make_subject_directory(subject_id, exercise_set=None)``
- ``set_id(subject_id)``
- ``finish()``
- ``receive_and_ignore(duration, no_print=False)``
- ``get_record(duration)``
- ``record_initial_rest(rest_time, movement, perform_time)``
- ``emg_recording(perform_time, rest_time, movement, rep)``

Notes
-----
- This controller does **not** perform I/O on its own; it only delegates.
- Extend this class to layer concerns like logging or telemetry without
  modifying UI code that depends on the recorder.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class RecorderProtocol(Protocol):
    """Protocol that concrete recorder implementations should satisfy.

    Methods
    -------
    make_subject_directory(subject_id, exercise_set=None)
        Create or ensure the subject's directory exists.
    set_id(subject_id)
        Set the current subject/session identifier.
    finish()
        Tear down the recording session and release resources.
    receive_and_ignore(duration, no_print=False)
        Read and discard samples for a duration.
    get_record(duration)
        Record and return a window of samples.
    record_initial_rest(rest_time, movement, perform_time)
        Record an initial rest period according to the recorder's protocol.
    emg_recording(perform_time, rest_time, movement, rep)
        Run one EMG recording repetition (perform + rest).
    """

    # Signatures intentionally broad to accommodate different backends
    def make_subject_directory(self, subject_id: int | str, exercise_set: Optional[str] = None) -> Any: ...
    def set_id(self, subject_id: int | str) -> Any: ...
    def finish(self) -> Any: ...
    def receive_and_ignore(self, duration: float, no_print: bool = False) -> Any: ...
    def get_record(self, duration: float) -> Any: ...
    def record_initial_rest(self, rest_time: float, movement: int, perform_time: float) -> Any: ...
    def emg_recording(self, perform_time: float, rest_time: float, movement: int, rep: int) -> Any: ...


class RecordingController:
    """
    Pass-through wrapper around a recorder instance.

    The controller forwards calls unchanged to the underlying recorder stored in
    ``self._rec``. This allows you to evolve cross-cutting behavior (e.g.,
    retry, logging, timing, tracing) in one place.

    Attributes
    ----------
    _rec : RecorderProtocol
        The underlying recorder object. It must implement the methods listed in
        the module's *Integration contract* section.
    """

    def __init__(self, recorder: RecorderProtocol) -> None:
        """Initialize the controller.

        Parameters
        ----------
        recorder : RecorderProtocol
            The concrete recorder to delegate to. It should provide the full set
            of methods expected by the UI (see module docs).
        """
        self._rec: RecorderProtocol = recorder

    # ---- direct pass-throughs (same signatures/semantics) ----

    def make_subject_directory(self, subject_id: int | str, exercise_set: Optional[str] = None) -> Any:
        """Create (or ensure) the subject's directory via the recorder.

        Parameters
        ----------
        subject_id : int | str
            Identifier for the subject (e.g., ``1`` or ``"S01"``).
        exercise_set : str, optional
            Optional exercise set/session label (e.g., ``"EA"`` or ``"EB"``).

        Returns
        -------
        Any
            Whatever the underlying recorder returns (e.g., a filesystem path or
            a boolean), unchanged.
        """
        return self._rec.make_subject_directory(subject_id, exercise_set=exercise_set)

    def set_id(self, subject_id: int | str) -> Any:
        """Set the current subject ID on the recorder.

        Parameters
        ----------
        subject_id : int | str
            Identifier to associate with subsequent recordings.

        Returns
        -------
        Any
            The recorder's return value, unchanged.
        """
        return self._rec.set_id(subject_id)

    def finish(self) -> Any:
        """Finish/teardown the recorder session.

        Returns
        -------
        Any
            The recorder's return value, unchanged.
        """
        return self._rec.finish()

    def receive_and_ignore(self, duration: float, no_print: bool = False) -> Any:
        """Receive samples for a duration but do not persist them.

        Typically used for device warm-up or to flush buffers.

        Parameters
        ----------
        duration : float
            Time interval to read (seconds).
        no_print : bool, default False
            If supported, suppress status prints.

        Returns
        -------
        Any
            The recorder's return value, unchanged.
        """
        return self._rec.receive_and_ignore(duration, no_print=no_print)

    def get_record(self, duration: float) -> Any:
        """Record and return a window of samples.

        Parameters
        ----------
        duration : float
            Time interval to record (seconds).

        Returns
        -------
        Any
            The recorder's return value (e.g., ``np.ndarray``), unchanged.
        """
        return self._rec.get_record(duration)

    def record_initial_rest(self, rest_time: float, movement: int, perform_time: float) -> Any:
        """Record an initial rest period according to the recorder's protocol.

        Parameters
        ----------
        rest_time : float
            Duration of the rest segment (seconds).
        movement : int
            Movement label/index to associate.
        perform_time : float
            Duration of the subsequent performance segment (seconds).

        Returns
        -------
        Any
            The recorder's return value, unchanged.
        """
        return self._rec.record_initial_rest(rest_time, movement, perform_time)

    def emg_recording(self, perform_time: float, rest_time: float, movement: int, rep: int) -> Any:
        """Run one EMG recording repetition.

        Parameters
        ----------
        perform_time : float
            Duration of the movement performance window (seconds).
        rest_time : float
            Duration of the subsequent rest window (seconds).
        movement : int
            Movement label/index to associate with this repetition.
        rep : int
            Repetition index/count.

        Returns
        -------
        Any
            The recorder's return value, unchanged.
        """
        return self._rec.emg_recording(perform_time, rest_time, movement, rep)

    def finish_safe(self) -> None:
        """Attempt :meth:`finish`, swallowing exceptions.

        Intended for shutdown paths where hard failures would be disruptive.

        Side Effects
        ------------
        Prints a diagnostic on exception; otherwise silent.
        """
        try:
            self._rec.finish()
        except Exception as e:  # pragma: no cover - defensive shutdown path
            print(f"[RecordingController.finish_safe] {e}")
