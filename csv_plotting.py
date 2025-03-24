import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
matplotlib.use('TkAgg')

def extract_movement_and_rep(file):
    base_name = os.path.basename(file)
    movement = int(base_name.split('_M')[1].split('R')[0])
    rep = int(base_name.split('R')[1].split('.csv')[0])
    return movement, rep
def plot_movement(folder_path, display_time=7):
    """
    Loops through all CSV files in a folder, displaying each for a given number of seconds.
    """
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv') and f'filtered_emg_data' in f]
    label_files = [f for f in os.listdir(folder_path) if f.endswith('.csv') and f'label' in f]
    label_files = sorted(label_files, key=extract_movement_and_rep)
    sorted_files = sorted(files, key=extract_movement_and_rep)

    for i, file in enumerate(sorted_files):
        file_path = os.path.join(folder_path, file)
        label_file_path = os.path.join(folder_path, label_files[i])

        data = np.loadtxt(file_path, delimiter=',')
        label = np.loadtxt(label_file_path, delimiter=',')
        label_mask = np.where(label > 0, 1, 0)
        label_starts = np.where(label_mask == 1)[0][0]
        label_ends = np.where(label_mask == 1)[0][-1]


        plt.clf()
        fig, axes = plt.subplots(nrows=32, ncols=1, figsize=(16, 16), sharex=True)
        movement, rep = extract_movement_and_rep(file)
        fig.suptitle(f'EMG data for movement {movement} repetition {rep}', fontsize=16)

        for j, emg_signal in enumerate(data[:32]):
            axes[j].set_ylim(-1000, 1000)
            axes[j].set_yticks([])
            axes[j].set_xticks([])
            axes[j].plot(emg_signal, label=f'Channel {j + 1}')
            axes[j].axvline(x=label_starts, color='r', linestyle='--', linewidth=2)
            axes[j].axvline(x=label_ends, color='r', linestyle='--', linewidth=2)



        manager = plt.get_current_fig_manager()
        manager.full_screen_toggle()
        plt.pause(0.5)
        plt.draw()
        plt.show(block=False)
        time.sleep(display_time)
        plt.close(fig)
    plt.show()


if __name__ == '__main__':

    plot_movement("emg_data", 10)
