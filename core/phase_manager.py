# core/phase_manager.py
"""
Fixed-duration phase manager for Tkinter-based UIs.

This module defines :class:`PhaseManager`, a small scheduler/animator that runs a
single **fixed-duration phase** (e.g., "Perform", "Rest"), updates labels, drives
a radial arc widget, and invokes a completion callback. It is UI-agnostic and
communicates exclusively via injected callables, making it easy to test and to
document with **mkdocstrings**.

Overview
--------
Responsibilities:
- Show a fixed time label (total time for the phase).
- Animate a radial arc by updating its extent (0–360°).
- Set a state label (e.g., "Rest", "Perform").
- Call an `on_done` callback when the phase completes.
- Support **pause**, **resume**, and **stop**, using a Tk-safe `after(...)`.

Injection points (provided by the host app):
- ``after(ms, fn)``: Typically ``root.after``; schedules the next tick.
- ``set_time_label(text)``: Updates the time label.
- ``set_state_label(text)``: Updates the state label.
- ``set_arc_extent_deg(deg)``: Sets arc extent in degrees (negative for clockwise).
- ``set_arc_color(color)``: Sets arc color.

Notes
-----
- The class does **not** own any Tk widgets; it only calls the provided
  functions. This avoids widget lifetime issues and keeps responsibilities
  separated.
- If the arc widget is destroyed during shutdown, animation updates are caught
  and ignored to prevent hard failures.

Example
-------
>>> import tkinter as tk
>>> root = tk.Tk()
>>>
>>> def after(ms, fn): root.after(ms, fn)
>>> def set_time_label(s): print("TIME:", s)
>>> def set_state_label(s): print("STATE:", s)
>>> def set_arc_extent_deg(d): pass  # your canvas item update here
>>> def set_arc_color(c): pass
>>>
>>> pm = PhaseManager(after, set_time_label, set_state_label,
...                   set_arc_extent_deg, set_arc_color, tick_ms=50)
>>> pm.start(duration_ms=1000, on_done=lambda: print("DONE"),
...          color="green", state_text="Perform")
>>> root.mainloop()
"""

from __future__ import annotations
from typing import Callable, Optional


class PhaseManager:
    """
    Owns the 'fixed-duration phase' behavior.

    It:
    - shows a fixed time label,
    - animates a radial arc via a setter,
    - calls a next-callback when the phase finishes,
    - supports pause/resume/stop cleanly (Tk-safe via injected ``after``).

    Parameters
    ----------
    after:
        Scheduler function, usually ``tk.Tk.after``: ``after(ms, callback)``.
    set_time_label:
        Callback to set the time label text.
    set_state_label:
        Callback to set the state label text.
    set_arc_extent_deg:
        Callback to set the arc extent in **degrees**. Negative values can be
        used to animate clockwise (typical in Tk canvas arcs).
    set_arc_color:
        Callback to set the arc color (e.g., hex string or Tk color name).
    tick_ms:
        Animation/logic tick in milliseconds. Defaults to ``50``.
    """

    def __init__(
        self,
        after: Callable[[int, Callable], None],
        set_time_label: Callable[[str], None],
        set_state_label: Callable[[str], None],
        set_arc_extent_deg: Callable[[int], None],
        set_arc_color: Callable[[str], None],
        tick_ms: int = 50,
    ):
        self._after = after
        self._set_time = set_time_label
        self._set_state = set_state_label
        self._set_extent = set_arc_extent_deg
        self._set_color = set_arc_color
        self._tick = tick_ms

        self._total_ms = 0
        self._remaining_ms = 0
        self._next: Optional[Callable[[], None]] = None
        self._stopped = False
        self._paused = False

    # lifecycle
    def stop(self) -> None:
        """Stop the manager permanently for the current phase.

        Sets an internal flag that prevents further scheduling/updates. Safe to
        call multiple times.
        """
        self._stopped = True

    def pause(self) -> None:
        """Pause the phase timer/animation.

        The manager stops ticking until :meth:`resume` is called. No callbacks
        are fired while paused.
        """
        self._paused = True

    def resume(self) -> None:
        """Resume ticking if paused and the phase is still active."""
        was_paused = self._paused
        self._paused = False
        if was_paused and not self._stopped and self._remaining_ms > 0:
            self._loop()

    # main API
    def start(self, duration_ms: int, on_done: Optional[Callable[[], None]], color: str, state_text: str) -> None:
        """Start a new fixed-duration phase.

        This sets labels, color, resets internal counters, and begins ticking.

        Args:
            duration_ms: Total phase duration in milliseconds. Values <= 0 will
                be clamped to 1 ms.
            on_done: Optional callback invoked (via ``after(0, ...)``) once the
                phase completes.
            color: Arc color to apply via ``set_arc_color`` at start.
            state_text: Text to show in the state label (e.g., ``"Rest"``).

        Notes:
            - If :meth:`stop` has been called, `start` becomes a no-op.
            - The time label displays the **total** time (not the remaining).
        """
        if self._stopped:
            return
        self._total_ms = max(1, int(duration_ms))
        self._remaining_ms = self._total_ms
        self._next = on_done
        self._set_time(f"Time: {self._total_ms/1000:.1f} s")
        self._set_state(f"State: {state_text}")
        self._set_color(color)
        self._loop()

    # internals
    def _loop(self) -> None:
        """Advance one tick: update arc extent and schedule the next tick.

        Internal method—safe against widget teardown. If the arc widget no
        longer exists, an exception may be raised by the extent setter; this is
        caught and the loop exits silently.
        """
        if self._stopped or self._paused:
            return
        frac = max(0.0, min(1.0, self._remaining_ms / self._total_ms)) if self._total_ms else 0.0
        extent = int(360 * frac)
        try:
            self._set_extent(-extent)
        except Exception:
            # widget may be destroyed during shutdown
            return

        if self._remaining_ms > 0:
            self._remaining_ms = max(0, self._remaining_ms - self._tick)
            self._after(self._tick, self._loop)
        else:
            cb = self._next
            if callable(cb):
                self._after(0, cb)
