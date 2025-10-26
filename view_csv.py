# view_csv.py
"""
Plotting utilities for EMG/EEG CSV files.

This module provides two helpers—:func:`plot_file` and :func:`plot_channel`—to
visualize signals stored in **comma-separated** text files. It is intended to be
indexed by **mkdocstrings** for inclusion in your MkDocs site.

Overview
--------
- **Multi-channel view**: stacked subplots with shared X; Y-limits normalized by
  ``AMPLITUDE_IN_MILLIVOLTS`` (interpreted as mV or µV depending on mode).
- **Single-channel view**: plots one channel, with a simple unit label heuristic.
- **Unit scaling**: a module flag ``MICRO_VOLTS`` controls mV→µV scaling.

⚠️ Unit heuristic & filename note
---------------------------------
``MICRO_VOLTS`` is determined **at import time** from the module-level
``FILENAME`` (True if its basename starts with ``"eeg"``). If you call
:func:`plot_file` or :func:`plot_channel` with a *different* path than
``FILENAME``, the heuristic will not update automatically.

- To force EEG scaling independently of ``FILENAME``, set:
  ``MICRO_VOLTS = True`` (or ``False``) **before** calling the plotting
  functions.
- Alternatively, set ``FILENAME = "<your path>"`` before import-time evaluation
  (or re-run the module) so the heuristic matches your file.

Matplotlib backend
------------------
This module requests the Tk backend via ``matplotlib.use("TkAgg")``. If you need
a different backend (e.g., when running headless), you should set it **before
importing** ``matplotlib.pyplot`` in your entry point. If you see a backend
warning, move the ``use(...)`` call earlier in your startup code.

Globals / Parameters
--------------------
- ``FILENAME``: Path used by the ``__main__`` block and for the EEG/mV→µV
  heuristic described above.
- ``SINGLE_CHANNEL_MODE`` / ``CHANNEL``: Toggles and selects the 1-based channel
  for :func:`plot_channel` in the ``__main__`` block.
- ``START_CHANNEL`` / ``NUM_CHANNELS`` / ``CHANNEL_LIST``: Control which
  channels are shown in multi-channel mode. ``CHANNEL_LIST`` expects **0-based
  indices**.
- ``AMPLITUDE_IN_MILLIVOLTS``: Amplitude clamp for multi-channel plots (interpreted
  as **mV** unless ``MICRO_VOLTS=True``, in which case it is treated as **µV**).

Assumptions
-----------
- CSV contains **numeric samples only** (no header). Adjust ``np.loadtxt`` kwargs
  (e.g., ``skiprows``) if your files include headers.
- Signals are arranged such that after ``transpose()``, data is
  ``(channels, samples)``. This works whether channels are rows or columns.

Example
-------
>>> # Force EEG scaling regardless of FILENAME
>>> MICRO_VOLTS = True
>>> plot_file("eeg_data.csv", channel_list=[0, 1, 2, 3])  # channels 1–4
>>> plot_channel("emg_data.csv", channel=12)              # 1-based index

Notes
-----
- ``config.Config`` is imported for potential future use but not currently used.
- For large CSVs, ``np.loadtxt`` can be slow; consider chunked reads or binary
  formats if performance becomes an issue.
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from config import Config
matplotlib.use('TkAgg')


FILENAME = ""                           # Set your file name here
SINGLE_CHANNEL_MODE = False
CHANNEL = 12

START_CHANNEL = 10
NUM_CHANNELS = 5

CHANNEL_LIST = []


AMPLITUDE_IN_MILLIVOLTS = 1               # Only affects multi-channel mode. Adjust as necessary


MICRO_VOLTS = False
if FILENAME.split("\\")[-1].startswith("eeg"):
    MICRO_VOLTS = True

def plot_file(file_path, channel_list=[]):
    """Plot multiple channels from a CSV signal file in stacked subplots.

    Loads the CSV at ``file_path``, transposes to ``(channels, samples)``,
    optionally selects a subset of channels, applies EEG µV scaling **depending
    on the module-level ``MICRO_VOLTS`` flag**, and renders each channel on its
    own axis with a shared X-axis.

    Parameters
    ----------
    file_path : str or pathlib.Path
        Path to the CSV file (channels in columns or rows; function transposes
        to channel-major).
    channel_list : Iterable[int], optional
        **0-based** indices of channels to include. If empty, all channels are
        plotted.

    Notes
    -----
    - When ``MICRO_VOLTS`` is True, data is multiplied by ``1e3`` to convert
      mV→µV for display.
    - The Y-range of each subplot is clamped to
      ``±AMPLITUDE_IN_MILLIVOLTS`` (interpreted as mV or µV depending on mode).
    """
    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()
    if len(channel_list) > 0:
        data = data[channel_list]

    amplitude = AMPLITUDE_IN_MILLIVOLTS
    if MICRO_VOLTS:
        data = data * 1e3
        amplitude = amplitude * 1e3
    print(data.shape)

    plt.clf()
    fig, axes = plt.subplots(nrows=data.shape[0], ncols=1, figsize=(16, 16), sharex=True)
    fig.suptitle(f'file: {file_path}', fontsize=16)
    X = 0

    for j, emg_signal in enumerate(data):
        axes[j].set_ylim(-1 * amplitude, amplitude)
        axes[j].set_yticks([])
        axes[j].set_xticks([])
        axes[j].plot(emg_signal, label=f'Channel {j + 1}')

    plt.show()

def plot_channel(file_path, channel=1):
    """Plot a single channel from a CSV signal file.

    Loads and transposes the CSV at ``file_path``, applies unit heuristics, and
    plots the specified **1-based** ``channel``.

    Unit label heuristic:
    - If the maximum value across channels 6–20 (1-based) exceeds ``500``,
      the Y-label is set to ``"raw input"`` (suggesting device counts).
    - Else, if ``MICRO_VOLTS`` is True, values are scaled to µV and label is
      ``"µV"``.
    - Otherwise, label defaults to ``"mV"``.

    Parameters
    ----------
    file_path : str or pathlib.Path
        Path to the CSV file.
    channel : int, default=1
        **1-based** channel index to visualize.

    Notes
    -----
    - The heuristic is intentionally simple; adjust thresholds/logic to match
      your acquisition pipeline (e.g., calibrated units vs. raw counts).
    """
    data = np.loadtxt(file_path, delimiter=',')
    data = data.transpose()
    unit_label = "mV"
    if max([max(x) for x in data[5:20]]) > 500:
        unit_label = "raw input"
    elif MICRO_VOLTS:
        data = data * 1e3
        unit_label = "µV"

    plt.clf()
    plt.figure(figsize=(15, 5))
    plt.ylabel(unit_label)

    plt.plot(data[channel-1])

    plt.show()


# Entry point: selects plotting mode based on flags/args and renders the figure.
if __name__ == '__main__':

    if SINGLE_CHANNEL_MODE:
        plot_channel(FILENAME, CHANNEL)
    elif len(CHANNEL_LIST) > 0:
        plot_file(FILENAME,  CHANNEL_LIST)
    elif START_CHANNEL and NUM_CHANNELS:
        plot_file(FILENAME, range(START_CHANNEL, START_CHANNEL + NUM_CHANNELS))
    else:
        plot_file(FILENAME)
