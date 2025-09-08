from scipy.signal import butter, filtfilt
import numpy as np

def eeg_highpass_filter(data, cutoff=0.1):
    nyq = 0.5 * 500
    b, a = butter(4, cutoff/nyq, btype="high")
    return filtfilt(b, a, data, axis=1)