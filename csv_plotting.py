import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')


def plot_movement(movement, folder_path, display_time=5):
    """
    Loops through all CSV files in a folder, displaying each for a given number of seconds.
    """
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv') and f'M{movement}' in f]
    print(files)

    for i, file in enumerate(files):
        file_path = os.path.join(folder_path, file)

        data = np.loadtxt(file_path, delimiter=',')

        plt.clf()

        # Plot each channel
        for j in range(data.shape[0]):
            plt.plot(data[j], label=f'Channel {j + 1}')

        plt.xlabel("Time (samples)")
        plt.ylabel("Amplitude")
        plt.title(f"EMG Data Plot: Movement {movement}, Repetition {i+1}")

        plt.pause(0.5)
        plt.draw()
        plt.show(block=False)
        time.sleep(display_time)
    plt.show()


if __name__ == '__main__':

    plot_movement(1, "emg_data", 3)
