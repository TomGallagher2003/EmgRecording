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
    data = bandstop_filter(data, 49, 51, order=2, fs=fs)   # 50 Hz
    data = bandstop_filter(data, 99, 101, order=2, fs=fs)  # 100 Hz
    return data
import numpy as np
from scipy.signal import butter, sosfiltfilt, firwin, filtfilt

def high_order_lowpass_filter(data, cutoff, order=4, fs=FS, axis=1):
    """
    Stable low-pass filter:
      - If order <= 12: Butterworth IIR in SOS form + sosfiltfilt (stable).
      - If order  > 12: Linear-phase FIR via firwin + filtfilt (very stable).
    Safe to call with order=70.
    """
    x = np.asarray(data, dtype=np.float64)

    # normalize shape/axis
    if x.ndim == 1:
        x = x[None, :] if axis == 1 else x[:, None]

    # sanitize bad values
    if not np.isfinite(x).all():
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)

    # basic checks
    nyq = 0.5 * fs
    if not (0 < cutoff < nyq):
        raise ValueError(f"cutoff must be between 0 and Nyquist ({nyq} Hz); got {cutoff}")

    # pick method based on order
    n_samples = x.shape[axis]

    if order <= 12:
        # IIR Butterworth in SOS form
        sos = butter(order, cutoff, btype="low", fs=fs, output="sos")
        # choose a safe padlen (must be < n_samples)
        # default padlen for sosfiltfilt is ~ 3 * (n_sections*2 - 1)
        n_sections = sos.shape[0]
        default_padlen = 3 * (2 * n_sections - 1)
        padlen = min(default_padlen, max(0, n_samples - 1))
        return sosfiltfilt(sos, x, axis=axis, padlen=padlen)
    else:
        # High "order" requested: use FIR for stability.
        # Map requested IIR order to a reasonable FIR length.
        # Rule of thumb: larger numtaps => sharper rolloff.
        # Start with 8x "order" and ensure odd length.
        numtaps = max(8 * order + 1, 129)
        if numtaps % 2 == 0:
            numtaps += 1

        taps = firwin(numtaps, cutoff=cutoff, fs=fs, pass_zero="lowpass")
        # filtfilt default padlen is 3 * (max(len(b), len(a)) - 1)
        default_padlen = 3 * (len(taps) - 1)
        padlen = min(default_padlen, max(0, n_samples - 1))
        return filtfilt(taps, [1.0], x, axis=axis, padlen=padlen)

def preprocess_eeg(data, fs=FS):
    """
      1. High-pass (5th order, 0.3 Hz)
      2. Band-stop at 50 Hz and 100 Hz
      3. Low-pass (70th order, 70 Hz cutoff)
    """
    data = highpass_filter(data, cutoff=0.3, order=5, fs=fs)
    data = remove_line_noise(data, fs=fs)
    data = high_order_lowpass_filter(data, cutoff=70, order=70, fs=fs)
    return data
