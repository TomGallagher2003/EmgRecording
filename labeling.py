import numpy as np
from config import Config
from movement_seperation import get_movement_mask, segment_multi_channel_emg_ste

for i in range(5):
    for j in range(2):

        emg_data = np.loadtxt(Config.DATA_DESTINATION_PATH + rf"\filtered_emg_data_M{i + 1}R{j+1}.csv", delimiter=',')

        labels = (np.where(get_movement_mask(emg_data, start_threshold=0.3, end_threshold=0.08, start_conf_time=30, end_conf_time=1200) == 1, i + 1, 0))
        # labels = (np.where(segment_multi_channel_emg_ste(emg_data) == 1, i + 1, 0))

        np.savetxt(Config.DATA_DESTINATION_PATH + rf"\label_M{i + 1}R{j+1}.csv", labels, delimiter=',')

        print("Saved labels")
