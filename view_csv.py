import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')

DEFAULT_FILENAME = "emg_data/1/EA/csv/emg_data_23-06_1000ms_M1R1.csv"  # default example filename
SINGLE_CHANNEL_MODE = True            # Set to True to see just the first channel, set to False to see all channels
AMPLITUDE = 0.7                        # You can adjust the amplitude here if the data goes off the edges of the graph

def plot_file(file_path):
    file_path
    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    plt.clf()
    fig, axes = plt.subplots(nrows=32, ncols=1, figsize=(16, 16), sharex=True)
    fig.suptitle(f'file: {filename}', fontsize=16)

    for j, emg_signal in enumerate(data):
        axes[j].set_ylim(-1 * AMPLITUDE, AMPLITUDE)
        axes[j].set_yticks([])
        axes[j].set_xticks([])
        axes[j].plot(emg_signal, label=f'Channel {j + 1}')

    plt.show()

def plot_channel(file_path, channel=0):
    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    plt.clf()
    plt.figure(figsize=(10, 6))
    plt.ylim((-1 * AMPLITUDE, AMPLITUDE))
    plt.plot(data[channel])
    plt.show()

if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILENAME

    if SINGLE_CHANNEL_MODE:
        plot_channel(filename)
    else:
        plot_file(filename)
