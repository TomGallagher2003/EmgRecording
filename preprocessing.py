import numpy as np
from scipy.signal import butter, lfilter
from config import Config

def butter_bandpass(lowcut, highcut, fs, order=5):
    return butter(order, [lowcut, highcut], fs=fs, btype='band')

def butter_bandpass_filter(data, lowcut, highcut, fs, order):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

# Butterworth specs as recommended
low = 20.0  # Lower corner frequency
high = 425.0  # Upper corner frequency
filter_order = 2  # 2nd order filter gives a slope of 12 dB/oct as recommended


data = np.loadtxt(Config.DATA_DESTINATION_PATH + rf"\emg_dataD_M{1}R{2}.csv", delimiter=',')

filtered_data = np.array([butter_bandpass_filter(data[i], low, high, Config.SAMPLE_FREQUENCY, filter_order) for i in range(data.shape[0])])

np.savetxt(Config.DATA_DESTINATION_PATH + rf"\filtered_emg_data_M{1}R{2}.csv", filtered_data, delimiter=',', fmt='%0.6f')

print("Saved processed data")