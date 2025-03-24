import math
import os
import numpy as np
from config import Config
import numpy as np


def get_movement_mask(data, start_threshold, end_threshold, start_conf_time, end_conf_time):
    mask = np.zeros(data.shape[1], dtype=bool)
    start, end = get_movement_window(data, start_threshold, end_threshold, start_conf_time, end_conf_time)
    mask[start:end] = 1
    return mask

def get_channel_movement_window(data, start_threshold_pct, end_threshold_pct, start_conf_time, end_conf_time):
    start_threshold = max(abs(data)) * start_threshold_pct
    end_threshold = max(abs(data)) * end_threshold_pct
    start = None
    for i in range(len(data)):
        if sum(abs(data[i:i+start_conf_time])) / start_conf_time > start_threshold:
            start = i
            break

    if start is None:
        return None, None

    end = None
    for i in range(start, len(data)):
        if abs(data[i]) < end_threshold:
            end = i
            # Ensure the signal stays below the threshold on average for a confirmation period
            if i + end_conf_time < len(data) and sum(abs(data[i:i + end_conf_time])) / end_conf_time < end_threshold and all([(sum(abs(data[i + (j-1)* int(end_conf_time/10):i + j* int(end_conf_time/10)])) / end_conf_time * 10 < end_threshold) for j in range(10)]) :
                break
    return start, end


def get_movement_window(data, start_threshold, end_threshold, start_conf_time, end_conf_time):
    starts, ends = np.array([]), np.array([])

    for i, channel in enumerate(data[Config.MUOVI_EMG_CHANNELS]):
        if i not in range(4, 16) :

            start, end = get_channel_movement_window(channel, start_threshold, end_threshold, start_conf_time, end_conf_time)

            if start is not None and end is not None:
                starts = np.append(starts, start)
                ends = np.append(ends, end)
    return int(np.median(starts)) - 100, int(np.median(ends))


def compute_ste(signal, window_size=50):
    ste = np.convolve(signal**2, np.ones(window_size), mode='same')
    return ste

def segment_multi_channel_emg_ste(data, threshold=0.2):
    num_channels = data.shape[0]
    movement_masks = np.zeros_like(data)

    for i in range(num_channels):  # Process each channel separately
        ste_signal = compute_ste(data[i])
        movement_masks[i] = ste_signal > threshold  # Apply threshold

    # Majority voting across channels
    final_mask = np.sum(movement_masks, axis=0) > (num_channels // 2)
    return final_mask
