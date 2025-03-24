import os
import numpy as np
from config import Config
import numpy as np


def get_movement_mask(length, start, end):
    mask = np.zeros(length, dtype=bool)
    mask[start:end] = 1

    return mask

def get_movement_window(data):
    return 1, 2



file_path = Config.DATA_DESTINATION_PATH + rf"\emg_dataD_M{1}R{2}.csv"

data_loaded = np.loadtxt(file_path, delimiter=',', dtype=int)

start, end = get_movement_window(data_loaded)

print(get_movement_mask(data_loaded.shape[0], start, end))

