import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
matplotlib.use('TkAgg')


def plot_movement(folder_path, display_time=7, show_rest=False):
    """
    Loops through all CSV files in a folder, displaying each for a given number of seconds.
    """
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv') and f'emg' in f]
    if not show_rest:
        files = [f for f in files if not f.endswith('rest.csv')]

    for i, file in enumerate(files):
        file_path = os.path.join(folder_path, file)

        data = np.loadtxt(file_path, delimiter=',')
        data = data.transpose()


        plt.clf()
        fig, axes = plt.subplots(nrows=32, ncols=1, figsize=(16, 16), sharex=True)
        fig.suptitle(f'file: {file}', fontsize=16)

        for j, emg_signal in enumerate(data):
            axes[j].set_ylim(-2000, 2000)
            axes[j].set_yticks([])
            axes[j].set_xticks([])
            axes[j].plot(emg_signal, label=f'Channel {j + 1}')



        manager = plt.get_current_fig_manager()
        manager.full_screen_toggle()
        plt.pause(0.5)
        plt.draw()
        plt.show(block=False)
        time.sleep(display_time)
        plt.close(fig)
    plt.show()


if __name__ == '__main__':

    plot_movement("emg_data/csv", 8, show_rest=True)
