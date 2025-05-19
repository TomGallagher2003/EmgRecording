import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')


FILENAME = "example_data.csv"           # Put the filename here and run this python file to view.
SINGLE_CHANNEL_MODE = False               # Set to True to see just the first channel, set to False to see all channels
AMPLITUDE = 0.7                          # You can adjust the amplitude here if the data goes off the edges of the graph

def plot_file(filename):
    """
    Loops through all CSV files in a folder, displaying each for a given number of seconds.
    """

    file_path = os.path.join("emg_data", "csv", filename)

    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    print(data[-3][2100:2110])
    print(data.shape)

    plt.clf()
    fig, axes = plt.subplots(nrows=32, ncols=1, figsize=(16, 16), sharex=True)
    fig.suptitle(f'file: {filename}', fontsize=16)

    for j, emg_signal in enumerate(data):
        axes[j].set_ylim(-1 * AMPLITUDE, AMPLITUDE)
        axes[j].set_yticks([])
        axes[j].set_xticks([])
        axes[j].plot(emg_signal, label=f'Channel {j + 1}')
        print(j)



    plt.show()

def plot_channel(filename, channel=0):
    """
    Plots the given emg data file.
    """

    file_path = os.path.join("emg_data", "csv", filename)

    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()

    print(data[-3][2100:2110])
    print(data.shape)

    plt.clf()
    plt.figure(figsize=(10, 6))
    plt.ylim((-1 * AMPLITUDE, AMPLITUDE))

    plt.plot(data[channel])



    plt.show()

if __name__ == '__main__':

    if SINGLE_CHANNEL_MODE:
        plot_channel(FILENAME)
    else:
        plot_file(FILENAME)
