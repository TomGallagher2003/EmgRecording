"""Simple plotting utilities for EMG/EEG CSV files.

Provides helpers to visualize one or more channels from a comma-separated
signal file. If the filename begins with 'eeg', values are treated as microvolts
(µV) and scaled accordingly. Multi-channel plots normalize Y-limits using the
`AMPLITUDE_IN_MILLIVOLTS` setting (mV by default).
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config

matplotlib.use('TkAgg')

DATA_DIRS = [f"./test_recordings/counter_recordings/{i + 1}/counters/E{m_set}/csv" for i in range(3) for m_set in ["A", "B"]]

def main(file_path):

    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()
    prev_emg, prev_eeg = data[1][0], data[2][0]
    misses = 0
    for i in range(1, len(data[1]))[3::4]:
        new_emg, new_eeg = data[1][i], data[2][i]
        if  int((4*(new_eeg - prev_eeg)) % 65536) != int((new_emg - prev_emg) % 65536):
            misses +=1
            #print(new_emg, prev_emg, new_eeg, prev_eeg, "->", int((4*(new_eeg - prev_eeg)) % 65536), int((new_emg - prev_emg) % 65536))
        prev_emg, prev_eeg = new_emg, new_eeg


    return misses, len(data[1])/4


def all():
    files = []
    for dir in DATA_DIRS:
        for f in [os.path.join(dir, f) for f in os.listdir(dir) if f.endswith(".csv") and "label" not in f and "rest" not in f]:
            files.append(f)
    total_misses, total_len = 0, 0
    for file in files:
        misses, lent = main(file)
        if misses > 0:
            print(f"{file}->{(misses / lent * 100):.2f}% desync rate")
        total_misses += misses
        total_len += lent
    print(f"\n\nOverall ----> {(total_misses / total_len * 100):.3f}% desync rate in {int(total_len)} samples from {len(files)} files")
if __name__ == '__main__':
    all()

