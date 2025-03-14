import tkinter as tk
from tkinter import ttk
import time

def sleep_with_bar(secs=5, message="Loading..."):
    """Shows a loading bar with a customizable message and a countdown."""
    root = tk.Tk()
    root.title("Waiting...")

    message_label = tk.Label(root, text=message, font=("Arial", 14), padx=20, pady=10)
    message_label.pack()

    progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress.pack(pady=20)

    countdown_label = tk.Label(root, text=f"{secs}", font=("Arial", 12), padx=20, pady=10)
    countdown_label.pack()

    def sleep_bar():
        """Updates the loading bar and shows a countdown."""
        for i in range(101):
            progress["value"] = i
            countdown_label.config(text=f"{int(secs - (secs * i / 100)) + 1}")
            root.update_idletasks()
            time.sleep(secs / 100)
        root.destroy()

    root.after(100, sleep_bar)  # Let it load
    root.mainloop()
