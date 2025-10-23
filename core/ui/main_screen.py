# ui/main_screen.py
import tkinter as tk
from core.phase_manager import PhaseManager

def build_main_ui(app, window_width: int, window_height: int, arc_tick_ms: int = 50) -> None:
    """Build the main run UI (current/next image, countdown, controls) and wire PhaseManager."""
    app.current_index = 0
    app.current_repeat = 0
    app.after_last_repeat = False
    app.start_time = None

    left = tk.Frame(app.root, width=window_width // 2, height=window_height)
    left.pack(side='left', fill='both', pady=50, padx=30)
    right = tk.Frame(app.root, width=window_width // 2, height=window_height + 30)
    right.pack(side='right', fill='both', pady=20)
    app.left_frame, app.right_frame = left, right

    app.next_image_label = tk.Label(left, highlightthickness=0)  # toggled red border in pre-rest
    app.next_image_label.pack(anchor='n', padx=10, pady=10)
    app.variable_label = tk.Label(left, text=app.get_variables_text(), font=("Helvetica", 14))
    app.variable_label.pack(anchor='n', padx=10, pady=10)
    app.runtime_label = tk.Label(left, text="Runtime: 0 s", font=("Helvetica", 16))
    app.runtime_label.pack(anchor='n', padx=10, pady=10)

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
