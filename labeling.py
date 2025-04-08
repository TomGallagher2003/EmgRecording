import os
import numpy as np

files = [f for f in os.listdir('./emg_data') if f.endswith('.csv') and f'sample_counter' in f]
prev = 0
max_val = 65535  # Replace with your counter's maximum value
prev = 0
for file in files:
    data = np.loadtxt('./emg_data/' + file, delimiter=',')
    current = data[-100]

    if current < prev:
        diff = ((max_val - prev) + current + 1) / 2000
    else:
        diff = (current - prev) / 2000
    print("-------------------------")
    print("length: ", len(data))
    print(f"diff = {diff} seconds")
    prev = current
    print(file[-8:-4], ": ", data[-10:])

