# ui/device_screen.py
import tkinter as tk

def build_device_screen(app, window_width: int, window_height: int) -> None:
    """Build and render the device selection screen on the given app."""
    frame = tk.Frame(app.root, width=window_width, height=window_height)
    frame.pack(fill='both', expand=True)
    app.device_frame = frame

    for r in (0, 4):
        frame.grid_rowconfigure(r, weight=1)
    for c in (0, 1):
        frame.grid_columnconfigure(c, weight=1)

    title = tk.Label(frame, text="Select Connected Devices", font=("Helvetica", 20))
    title.grid(row=1, column=0, columnspan=2, pady=20)

    app.emg_var = tk.BooleanVar(value=False)
    app.eeg_var = tk.BooleanVar(value=False)

    emg_cb = tk.Checkbutton(
        frame, text="EMG", variable=app.emg_var, font=("Helvetica", 16),
        command=app._validate_device_selection
    )
    eeg_cb = tk.Checkbutton(
        frame, text="EEG", variable=app.eeg_var, font=("Helvetica", 16),
        command=app._validate_device_selection
    )
    emg_cb.grid(row=2, column=0, pady=10)
    eeg_cb.grid(row=2, column=1, pady=10)

    app.device_error = tk.Label(frame, text="", fg="red", font=("Helvetica", 12))
    app.device_error.grid(row=3, column=0, columnspan=2, pady=5)

    app.device_continue_btn = tk.Button(
        frame, text="Continue", font=("Helvetica", 16),
        state='disabled', command=app._confirm_devices
    )
    app.device_continue_btn.grid(row=4, column=0, columnspan=2, pady=30)
