#!/usr/bin/env python3

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')

from util.channel_alignment import find_eeg_counter
from util.OTB_refactored.configuration_processing import process_config
from config import Config

# === User configuration: define your raw buffer file here ===
BUFFER_FILE = Path("test/buffers", "buffer_both_M3R2.bin")


def load_and_align_buffer(buffer_file: Path):
    """
    Load a raw data buffer from a binary file and apply channel alignment.
    Returns the aligned buffer and the computed offset.
    """
    raw = buffer_file.read_bytes()
    offset = find_eeg_counter(raw)
    print(f"Alignment offset: {offset} bytes")
    if offset:
        raw = raw[:-offset]
    return raw, offset


def process_buffer(raw: bytes, tot_num_byte: int, tot_num_chan: int):
    """
    Process an aligned buffer into a (channels x samples) data array.
    """
    # Trim incomplete sample at start
    rem = len(raw) % tot_num_byte
    if rem:
        raw = raw[rem:]

    arr = np.frombuffer(raw, dtype=np.uint8)
    samples = arr.size // tot_num_byte
    temp = arr.reshape((samples, tot_num_byte)).T  # shape: (bytes, samples)

    # container for reconstructed channels
    data = np.zeros((tot_num_chan, samples), dtype=np.float32)
    chan_idx = 0

    # Per-device data
    for DevId in range(16):
        if Config.DEVICE_EN[DevId] != 1:
            continue
        if Config.EMG[DevId] == 1:
            # EMG channels
            ch_ind = np.arange(0, 33*2, 2)
            ch_ind_aux = np.arange(33*2, 38*2, 2)
            sub = temp[ch_ind].astype(np.int32) * 256 + temp[ch_ind+1].astype(np.int32)
            sub_aux = temp[ch_ind_aux].astype(np.int32) * 256 + temp[ch_ind_aux+1].astype(np.int32)

            # two's complement
            neg = sub >= 32768
            sub[neg] -= 65536
            # convert to mV
            sub = sub * Config.EMG_GAIN_RATIOS[Config.EMG_MODE] * 1e3

            data[chan_idx:chan_idx+33, :] = sub
            data[chan_idx+33:chan_idx+38, :] = sub_aux
            chan_idx += Config.NUM_CHAN[DevId]
        else:
            # EEG channels
            start = Config.MUOVI_PLUS_EEG_CHANNELS[0] * 2
            ch_ind = np.arange(start, start + 64*3, 3)
            ch_ind_aux = np.arange(start + 64*3, start + 64*3 + 6*3, 3)
            sub = (temp[ch_ind].astype(np.int32) * 65536 +
                   temp[ch_ind+1].astype(np.int32) * 256 +
                   temp[ch_ind+2].astype(np.int32))
            sub_aux = (temp[ch_ind_aux].astype(np.int32) * 65536 +
                       temp[ch_ind_aux+1].astype(np.int32) * 256 +
                       temp[ch_ind_aux+2].astype(np.int32))

            neg = sub >= 8388608
            sub[neg] -= 16777216

            data[chan_idx:chan_idx+64, :] = sub
            data[chan_idx+64:chan_idx+70, :] = sub_aux
            chan_idx += Config.NUM_CHAN[DevId]

    # syncstation auxiliary channels
    aux_start = tot_num_byte - (6 * 2)
    ch_ind = np.arange(aux_start, aux_start + 6*2, 2)
    aux = temp[ch_ind].astype(np.int32) * 256 + temp[ch_ind+1].astype(np.int32)
    data[chan_idx:chan_idx+6, :] = aux

    return data


def plot_alignment(data: np.ndarray):
    """
    Plot key channels to visualize alignment with wider figures.
    """
    sync_counter = data[Config.SYNCSTATION_CHANNELS[-1]]
    print("syncstation counter index:", Config.SYNCSTATION_CHANNELS[-1])
    print("Data shape:", data.shape)

    # Wider figure for counters
    plt.figure(figsize=(12, 6))
    plt.plot(sync_counter, label='SyncStation Counter')
    plt.xlabel('Sample Index')
    plt.ylabel('Counter Value')
    plt.title('SyncStation Counter After Alignment')
    plt.legend()
    plt.tight_layout()
    plt.show()

    # Wider figure for EMG channel 0
    plt.figure(figsize=(12, 6))
    plt.plot(data[0], label='EMG Ch 1')
    plt.xlabel('Sample Index')
    plt.ylabel('Signal (mV)')
    plt.title('EMG Channel 1 After Processing')
    plt.tight_layout()
    plt.show()

    # Wider figure for EMG channel 32
    plt.figure(figsize=(12, 6))
    plt.plot(data[32], label='EMG Ch 32')
    plt.xlabel('Sample Index')
    plt.ylabel('Signal (mV)')
    plt.title('EMG Channel 32 After Processing')
    plt.tight_layout()
    plt.show()

# === Run alignment test ===
raw, offset = load_and_align_buffer(BUFFER_FILE)
_, _, _, tot_num_chan, tot_num_byte, _ = process_config(
    Config.DEVICE_EN, Config.EMG, Config.MODE, Config.NUM_CHAN
)
data = process_buffer(raw, tot_num_byte, tot_num_chan)
plot_alignment(data)
