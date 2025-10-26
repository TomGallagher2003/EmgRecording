# ui/main_screen.py
import tkinter as tk
from core.phase_manager import PhaseManager

"""Main run screen (UI) builder.

This module exposes a single helper, :func:`build_main_ui`, which constructs the
right/left panes, image widgets, labels, radial countdown canvas, and control
buttons. It also wires a :class:`core.phase_manager.PhaseManager` instance into
the provided ``app`` so the timer/arc can be driven from the main app logic.

The function mutates attributes on ``app`` (the Tk application/controller object)
to attach the created widgets and runtime state. It **does not** start any
timers or threads — it only builds UI and connects PhaseManager callbacks.
"""

def build_main_ui(app, window_width: int, window_height: int, arc_tick_ms: int = 50) -> None:
    """Build the main run UI (current/next image, countdown, controls).

    This function creates and packs the left/right frames, sets up the primary
    image display and “next” preview, renders static labels (variables/runtime),
    and builds the radial countdown canvas and control buttons. Finally, it
    instantiates :class:`core.phase_manager.PhaseManager` and wires its callbacks
    to the newly created canvas/labels so the host app can drive phase timing.

    Args:
        app: The controller object that holds Tk root and callbacks. It must
            provide:
                - ``root``: :class:`tk.Tk`
                - UI callbacks: ``pause_exercise()``, ``resume_exercise()``,
                  ``stop_session()``, ``get_variables_text()``
            This function will **attach** the following attributes on ``app``:
                ``left_frame``, ``right_frame``, ``next_image_label``,
                ``variable_label``, ``runtime_label``, ``image_label``,
                ``time_label``, ``index_label``, ``canvas``, ``arc``,
                ``pause_button``, ``resume_button``, ``stop_button``, ``phase``.
        window_width: Total window width in pixels; used for layout/sizing math.
        window_height: Total window height in pixels.
        arc_tick_ms: PhaseManager redraw interval for the radial arc (ms). Lower
            values animate more smoothly at higher CPU cost. Typical range:
            16–100 ms.

    Returns:
        None. Widgets are created and assigned on ``app``; no timers are started.

    Notes:
        - The phase *time* label is driven by :class:`PhaseManager`; by default
          this app shows a fixed per-phase value (not ticking down).
        - The “state” label is unused in this UI; we pass a no-op callback.
    """
    # Reset runtime state for a new session screen
    app.current_index = 0
    app.current_repeat = 0
    app.after_last_repeat = False
    app.start_time = None

    # Left / right columns
    left = tk.Frame(app.root, width=window_width // 2, height=window_height)
    left.pack(side='left', fill='both', pady=50, padx=30)
    right = tk.Frame(app.root, width=window_width // 2, height=window_height + 30)
    right.pack(side='right', fill='both', pady=20)
    app.left_frame, app.right_frame = left, right

    # Left: next image preview + session variables + runtime
    app.next_image_label = tk.Label(left, highlightthickness=0)  # toggled red border in pre-rest
    app.next_image_label.pack(anchor='n', padx=10, pady=10)
    app.variable_label = tk.Label(left, text=app.get_variables_text(), font=("Helvetica", 14))
    app.variable_label.pack(anchor='n', padx=10, pady=10)
    app.runtime_label = tk.Label(left, text="Runtime: 0 s", font=("Helvetica", 16))
    app.runtime_label.pack(anchor='n', padx=10, pady=10)

    # Right: main image + labels
    app.image_label = tk.Label(right)
    app.image_label.pack(pady=10, padx=window_width * 0.1)

    app.time_label = tk.Label(right, text="", font=("Helvetica", 16))
    app.time_label.pack(pady=10)
    app.index_label = tk.Label(right, text="", font=("Helvetica", 16))
    app.index_label.pack(pady=10)

    # Radial countdown indicator
    app.canvas = tk.Canvas(app.right_frame, width=60, height=80)
    app.canvas.pack(pady=10)
    app.canvas.create_oval(12, 12, 50, 50, outline='#ddd', width=8)
    app.arc = app.canvas.create_arc(12, 12, 50, 50, start=90, extent=0,
                                    style='arc', width=8)

    # Controls
    app.pause_button = tk.Button(left, text="Pause", font=("Helvetica", 16),
                                 fg="black", bg="red", command=app.pause_exercise)
    app.pause_button.pack(pady=10)

    app.resume_button = tk.Button(left, text="Resume", font=("Helvetica", 16),
                                  fg="black", bg="green", command=app.resume_exercise)
    app.stop_button = tk.Button(left, text="Stop Session", font=("Helvetica", 16),
                                fg="white", bg="black", command=app.stop_session)

    # Wire PhaseManager (state label not used in this UI, pass no-op)
    app.phase = PhaseManager(
        after=app.root.after,
        set_time_label=lambda s: app.time_label.config(text=s),
        set_state_label=lambda _s: None,
        set_arc_extent_deg=lambda deg: app.canvas.itemconfigure(app.arc, extent=deg),
        set_arc_color=lambda c: app.canvas.itemconfigure(app.arc, outline=c),
        tick_ms=arc_tick_ms,
    )
