from scipy.signal import butter, filtfilt
import numpy as np

FS = 500.0  # sampling frequency (Hz)

def highpass_filter(data, cutoff=0.1, order=4, fs=FS):
    nyq = 0.5 * fs
    b, a = butter(order, cutoff / nyq, btype="high")
    return filtfilt(b, a, data, axis=1)

def lowpass_filter(data, cutoff, order=4, fs=FS):
    nyq = 0.5 * fs
    b, a = butter(order, cutoff / nyq, btype="low")
    return filtfilt(b, a, data, axis=1)

def bandpass_filter(data, low, high, order=4, fs=FS):
    nyq = 0.5 * fs
    low_norm = low / nyq
    high_norm = high / nyq
    b, a = butter(order, [low_norm, high_norm], btype="band")
    return filtfilt(b, a, data, axis=1)

def bandstop_filter(data, low, high, order=2, fs=FS):
    nyq = 0.5 * fs
    low_norm = low / nyq
    high_norm = high / nyq
    b, a = butter(order, [low_norm, high_norm], btype="bandstop")
    return filtfilt(b, a, data, axis=1)


def remove_line_noise(data, fs=FS):
    """Remove 50 Hz and 100 Hz line noise with 2nd-order bandstop filters."""
    data = bandstop_filter(data, 49.9, 50.1, order=2, fs=fs)   # 50 Hz
    #data = bandstop_filter(data, 99, 101, order=2, fs=fs)  # 100 Hz
    return data
import numpy as np
from scipy.signal import butter, sosfiltfilt, firwin, filtfilt


def preprocess_eeg(data, fs=FS):
    """
      1. High-pass (5th order, 0.3 Hz)
      2. Band-stop at 50 Hz and 100 Hz
      3. Low-pass (70th order, 70 Hz cutoff)
    """
    data = highpass_filter(data, cutoff=0.3, order=2, fs=fs)
    data = remove_line_noise(data, fs=fs)
    data = lowpass_filter(data, cutoff=70, order=2, fs=fs)
    return data
