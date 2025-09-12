import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
matplotlib.use('TkAgg')


FILENAME = "eeg_debug_filtered_converted.csv"
MICRO_VOLTS = True           # When set to 'False', the default unit plotted is millivolts
AMPLITUDE = 10               # In mV, will be converted to µV when plotting in microvolts

def plot_file(file_path):
    """
    Plots the given emg data file.
    """


    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    amplitude = AMPLITUDE
    if MICRO_VOLTS:
        data = data * 1e3
        amplitude = amplitude * 1e3
    print(data.shape)


    plt.clf()
    fig, axes = plt.subplots(nrows=data.shape[0], ncols=1, figsize=(16, 16), sharex=True)
    fig.suptitle(f'file: {file_path}', fontsize=16)
    X = 0

    for j, emg_signal in enumerate(data):
        axes[j].set_ylim(-1 * amplitude, amplitude)
        axes[j].set_yticks([])
        axes[j].set_xticks([])
        axes[j].plot(emg_signal, label=f'Channel {j + 1}')



    plt.show()
def plot_channel(file_path, channel=1):
    """
    Plots the given emg data file.
    """


    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()
    unit_label = "mV"
    if max([max(x) for x in data[5:20]]) > 500:
        unit_label = "raw input"
    elif MICRO_VOLTS:
        data = data * 1e3
        unit_label = "µV"
    
    

    plt.clf()
    plt.figure(figsize=(15, 5))
    plt.ylabel(unit_label)

    plt.plot(data[channel-1])



    plt.show()

if __name__ == '__main__':

    #plot_channel(FILENAME, 12)

    plot_channel("unplugged_eeg_debug_filtered.csv", 12)
    plot_channel("data\\1091\eeg\EA\csv\eeg_data_12-09_2000ms_M1R1_filtered.csv", 12)

    plot_channel("unplugged_eeg_debug_filtered_converted.csv", 12)
    plot_channel("data\\1091\eeg\EA\csv\eeg_data_12-09_2000ms_M1R1_filtered_converted.csv", 12)

    #plot_file(FILENAME)
