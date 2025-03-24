import numpy as np
from scipy.signal import butter, lfilter
from config import Config

def butter_highpass(cutoff, fs, order):
    # Butterworth low-pass filter
    return butter(order, cutoff, fs=fs, btype='high')

def butter_highpass_filter(data, cutoff, fs, order):
    b, a = butter_highpass(cutoff, fs, order)
    y = lfilter(b, a, data)
    return y

# Butterworth specs as recommended
low = 50.0  # Lower corner frequency
filter_order = 2  # 2nd order filter gives a slope of 12 dB/oct as recommended
def preprocess(data, move, rep):

    # Apply butterworth filtering
    filtered_data = np.array([butter_highpass_filter(data[i], low, Config.SAMPLE_FREQUENCY, filter_order) for i in
                              range(data.shape[0])])

    # Save
    np.savetxt(Config.DATA_DESTINATION_PATH + rf"\filtered_emg_data_M{move}R{rep}.csv", filtered_data, delimiter=',',
               fmt='%0.6f')

for i in range(5):
    for j in range(2):

        emg_data = np.loadtxt(Config.DATA_DESTINATION_PATH + rf"\emg_data_M{i + 1}R{j+1}.csv", delimiter=',')

        preprocess(emg_data, i+1, j+1)

        print("Saved processed data")