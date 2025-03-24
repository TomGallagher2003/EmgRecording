import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config

matplotlib.use('TkAgg')


def plot_channel(raw_file, processed_file, channel):
    """Plots the raw and processed data of a single channel from an EMG data file."""
    raw_data = np.loadtxt(raw_file, delimiter=',')
    processed_data = np.loadtxt(processed_file, delimiter=',')

    plt.figure(figsize=(20, 6))

    # Raw data subplot
    plt.subplot(2, 1, 1)
    plt.ylim(-1000, 1000)
    plt.title('Raw EMG Signal')
    plt.plot(raw_data[channel])

    # Processed data subplot
    plt.subplot(2, 1, 2)
    plt.ylim(-1000, 1000)
    plt.title('Filtered EMG Signal')
    plt.plot(processed_data[channel])

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    raw_file = "emg_data/emg_data_M2R2.csv"  # Update with actual file path
    processed_file = "emg_data/filtered_emg_data_M1R2.csv"  # Update with actual processed file path
    plot_channel(raw_file, processed_file, 21)
