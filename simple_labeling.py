import os

import numpy as np
from config import Config
from movement_seperation import get_movement_mask, segment_multi_channel_emg_ste

files = [f for f in os.listdir(Config.DATA_DESTINATION_PATH) if f.endswith('.csv') and f'emg' in f and f'R1' in f]
for i, file in enumerate(files):


    print("Saved labels")
