# ui/device_screen.py
"""
Device selection screen (Tkinter) for EMG/EEG recording UI.

This module provides a single helper, `build_device_screen`, which constructs
the **device selection page** of the Tkinter app. It is designed to be
discovered by **mkdocstrings** for inclusion in your MkDocs site.

Overview
--------
The screen lets a user select which devices are connected (EMG, EEG), validates
that at least one device is chosen, and exposes a **Continue** button that hands
control back to the host application.

UI layout (grid):
- Row 1: Title "Select Connected Devices"
- Row 2: Two checkboxes: **EMG** (left), **EEG** (right)
- Row 3: Inline validation/error label (red)
- Row 4: **Continue** button (disabled until a device is checked)

Integration contract
--------------------
`build_device_screen(app, ...)` attaches several variables and widgets to the
`app` object and wires two callbacks that are expected to be implemented on
`app`:

Required callbacks on `app`:
- `_validate_device_selection() -> None`
    Called whenever either checkbox is toggled. Should enable the Continue
    button and clear the error when at least one device is selected; otherwise
    disable the button and show an error.
- `_confirm_devices() -> None`
    Called when the **Continue** button is pressed. Typically persists the
    selections and advances to the parameter screen.

Attributes added to `app`:
- `device_frame (tk.Frame)`: The root frame for this screen.
- `emg_var (tk.BooleanVar)`: Backing var for the EMG checkbox.
- `eeg_var (tk.BooleanVar)`: Backing var for the EEG checkbox.
- `device_error (tk.Label)`: Inline error/validation message (red).
- `device_continue_btn (tk.Button)`: Disabled until selection is valid.

Example
-------
>>> import tkinter as tk
>>> from ui.device_screen import build_device_screen
>>>
>>> class MyApp:
...     def __init__(self):
...         self.root = tk.Tk()
...         build_device_screen(self, 1200, 600)
...
...     def _validate_device_selection(self):
...         enabled = self.emg_var.get() or self.eeg_var.get()
...         self.device_continue_btn.config(state='normal' if enabled else 'disabled')
...         self.device_error.config(text="" if enabled else "Please select at least one device (EEG and/or EMG).")
...
...     def _confirm_devices(self):
...         # Handle selections and navigate to the next screen
...         pass
>>>
>>> app = MyApp()
>>> app.root.mainloop()

Notes
-----
- This module does not perform any device I/O; it is purely a UI builder.
- The host application owns navigation and lifecycle (e.g., destroying this
  frame when moving to the next screen).
"""

import tkinter as tk


def build_device_screen(app, window_width: int, window_height: int) -> None:
    """Build and render the device selection screen on the given app.

    This constructs a centered two-column grid with EMG/EEG checkboxes, an
    inline validation label, and a disabled **Continue** button that becomes
    enabled when at least one device is selected. All widgets/variables needed
    later by the app are attached to `app` for convenient access.

    Args:
        app: Host object that must expose a `root` attribute (``tk.Tk`` or
            ``tk.Frame``) and implement the callbacks:
            - ``_validate_device_selection()``: invoked on checkbox toggle
            - ``_confirm_devices()``: invoked by the Continue button
        window_width (int): Logical width allocation for the frame.
        window_height (int): Logical height allocation for the frame.

    Side Effects:
        - Assigns ``app.device_frame``, ``app.emg_var``, ``app.eeg_var``,
          ``app.device_error``, and ``app.device_continue_btn``.
        - Registers event handlers to ``app._validate_device_selection`` and
          ``app._confirm_devices``.

    See Also:
        The module docstring for an integration example and the list of
        attributes created on ``app``.
    """
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
