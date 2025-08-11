import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
matplotlib.use('TkAgg')


FILENAME = "data/3/EB/csv/emg_data_11-08_2000ms_M13R1.csv"  # Put the filename here and run this python file to view.
AMPLITUDE = 0.7                  # Adjust the amplitude here if the data goes off the edges of the graph

def plot_file(file_path):
    """
    Plots the given emg data file.
    """


    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    print(data.shape)

    plt.clf()
    fig, axes = plt.subplots(nrows=data.shape[0], ncols=1, figsize=(16, 16), sharex=True)
    fig.suptitle(f'file: {file_path}', fontsize=16)
    X = 0

    for j, emg_signal in enumerate(data):
        axes[j].set_ylim(-1 * AMPLITUDE, AMPLITUDE)
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
    print(data[channel-1][0:5])

    plt.clf()
    plt.figure(figsize=(15, 5))

    plt.plot(data[channel-1])



    plt.show()

if __name__ == '__main__':

    plot_channel(FILENAME, 32)
    #plot_file(FILENAME)
