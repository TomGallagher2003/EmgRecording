import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
matplotlib.use('TkAgg')


FILENAME = "emg_data_ID88_18-05_M1R2.csv"  # Put the filename here and run ths python file to view.
AMPLITUDE = 0.7                            # You can adjust the amplitude here if the data goes off the edges of the graph

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


if __name__ == '__main__':

    plot_file(FILENAME)
