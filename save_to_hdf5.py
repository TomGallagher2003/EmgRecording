import h5py
import numpy as np
from config import Config

for i in range(5):
    for j in range(2):

        emg_data = np.loadtxt(Config.DATA_DESTINATION_PATH + rf"\filtered_emg_data_M{i + 1}R{j+1}.csv", delimiter=',')
        labels = np.loadtxt(Config.DATA_DESTINATION_PATH + rf"\label_M{i + 1}R{j+1}.csv", delimiter=',')

        with h5py.File(Config.DATA_DESTINATION_PATH + rf"\hdf5\emg_data_M{i + 1}R{j+1}.h5", 'w') as hf:
            hf.create_dataset('emg_data', data=emg_data.transpose())
            hf.create_dataset("label", data=labels)

        print("Saved as hdf5")