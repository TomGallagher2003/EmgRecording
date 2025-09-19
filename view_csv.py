import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
matplotlib.use('TkAgg')


FILENAME = ""                           # Set your file name here
SINGLE_CHANNEL_MODE = False
CHANNEL = 12

START_CHANNEL = 10
NUM_CHANNELS = 5

CHANNEL_LIST = []




AMPLITUDE_IN_MILLIVOLTS = 1               # Only affects multi-channel mode. Adjust as necessary


MICRO_VOLTS = False
if FILENAME.split("\\")[-1].startswith("eeg"):
    MICRO_VOLTS = True

def plot_file(file_path, channel_list=[]):
    """
    Plots the given emg data file.
    """


    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()
    if len(channel_list) > 0:
        data = data[channel_list]


    amplitude = AMPLITUDE_IN_MILLIVOLTS
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


    if SINGLE_CHANNEL_MODE:
        plot_channel(FILENAME, CHANNEL)
    elif len(CHANNEL_LIST) > 0:
        plot_file(FILENAME,  CHANNEL_LIST)
    elif START_CHANNEL and NUM_CHANNELS:
        plot_file(FILENAME, range(START_CHANNEL, START_CHANNEL + NUM_CHANNELS))
    else:
        plot_file(FILENAME)
