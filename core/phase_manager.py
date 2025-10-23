# core/phase_manager.py
from __future__ import annotations
from typing import Callable, Optional

class PhaseManager:
    """
    Owns the 'fixed-duration phase' behavior:
    - shows a fixed time label,
    - animates a radial arc via a setter,
    - calls a next-callback when the phase finishes,
    - supports pause/resume/stop cleanly (Tk-safe via injected root.after).
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
        self._stopped = True

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        was_paused = self._paused
        self._paused = False
        if was_paused and not self._stopped and self._remaining_ms > 0:
            self._loop()

    # main API
    def start(self, duration_ms: int, on_done: Optional[Callable[[], None]], color: str, state_text: str) -> None:
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
