import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')

def view_label_csv(label_csv: str, sample_rate: int = 2000):
    """
    Load and plot the label CSV (0s and 1s).
    Shows where the 1-second region got marked.

    Args:
        label_csv: Path to the label CSV (e.g., 'online_label.csv').
        sample_rate: Sampling frequency (default=500 Hz for EEG).
    """
    labels = np.loadtxt(label_csv, delimiter=",", dtype=int)
    n_samples = len(labels)
    t = np.arange(n_samples) / sample_rate

    plt.figure(figsize=(10, 3))
    plt.plot(t, labels, drawstyle="steps-pre")
    plt.xlabel("Time (s)")
    plt.ylabel("Label")
    plt.title(f"Label timeline from {label_csv}")
    plt.ylim(-0.1, 1.1)
    plt.grid(True, axis="y")
    plt.show()

    # Also print indices of labeled region
    labeled_indices = np.where(labels == 1)[0]
    if labeled_indices.size > 0:
        start, end = labeled_indices[0], labeled_indices[-1]
        print(f"Labeled region: {start/sample_rate:.2f}s → {end/sample_rate:.2f}s "
              f"({(end-start+1)/sample_rate:.2f}s long)")
    else:
        print("No labeled region found.")

view_label_csv("online_label.csv", sample_rate=2000)
