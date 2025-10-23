# ui/parameter_screen.py
import tkinter as tk
from tkinter import ttk

def build_parameter_screen(app, window_width: int, window_height: int) -> None:
    """Render the parameter entry form (subject, durations, repeats, set)."""
    frame = tk.Frame(app.root, width=window_width, height=window_height)
    frame.pack(fill='both', expand=True)
    app.param_frame = frame

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
    app.entries = []
    for i, text in enumerate(labels, start=1):
        tk.Label(frame, text=text, font=("Helvetica", 14)).grid(row=i, column=0, sticky='e', padx=20, pady=10)
        entry = tk.Entry(frame, font=("Helvetica", 14))
        entry.grid(row=i, column=1, sticky='w', padx=20, pady=10)
        entry.bind('<KeyRelease>', lambda _e: app._validate_entries())
        app.entries.append(entry)

    (app.subject_id_entry,
     app.perform_time_entry,
     app.rest_time_entry,
     app.num_repeats_entry) = app.entries

    tk.Label(frame, text="Exercise Set (A, B, AB):", font=("Helvetica", 14)) \
        .grid(row=6, column=0, sticky='e', padx=20, pady=10)

    combo = ttk.Combobox(
        frame, textvariable=app.exercise_set_var, font=("Helvetica", 14),
        values=["A", "B", "AB"], state='readonly'
    )
    combo.grid(row=6, column=1, sticky='w', padx=20, pady=10)
    combo.bind('<<ComboboxSelected>>', lambda _e: app._validate_entries())
    app.exercise_set_combobox = combo

    btn = tk.Button(frame, text="Start Session", font=("Helvetica", 16),
                    state='disabled', command=app._start_session)
    btn.grid(row=7, column=0, columnspan=2, pady=30)
    app.start_button = btn
