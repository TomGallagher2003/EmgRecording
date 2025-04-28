import os
import glob
import numpy as np



for m in range(2, 4):
    data = np.loadtxt(f"./emg_data/sample_counter_M{m}rest.csv", delimiter=',')
    first_three = data[:3]

    print(f"File: M{m} rest")
    print(first_three.tolist())
    for r in range(1, 4):

        data = np.loadtxt(f"./emg_data/sample_counter_M{m}R{r}.csv", delimiter=',')
        first_three = data[:3]

        print(f"File: M{m}R{r}")
        print(first_three.tolist())
