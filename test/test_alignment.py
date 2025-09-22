"""Alignment validation utilities for EEG+EMG combined frames.

This module loads recorded raw buffers, applies byte alignment, decodes
channel data, and tests whether sample counters increment as expected.
It is primarily used for debugging SyncStation data alignment across
EEG and EMG devices.
"""

import time

import numpy as np

from config import Config
from util.buffer_functions import load_buffer
from debug.eeg_offset_util import offset_with_eeg  # updated version above
from util.processing import process

tot_num_byte = 298
tot_num_chan = 114
default_num_samples = 4000

slice_length = 12
slice_start = 5
print_slice = True

def _chan_width_bytes(ch_1based: int) -> int:
    """Return storage width in bytes for a given 1-based channel index.

    Args:
        ch_1based (int): Channel index starting at 1.

    Returns:
        int: Number of bytes used to encode samples for this channel.

    Raises:
        ValueError: If channel index is out of supported range.
    """

    if 1 <= ch_1based <= 38:    return 2
    if 39 <= ch_1based <= 108:  return 3
    if 109 <= ch_1based <= 114: return 2
    raise ValueError

def _score_periodic(vals: np.ndarray, width_bytes: int, period: int) -> tuple[float, int]:
    """Score how well a channel behaves like a periodic counter.

Computes how often a sequence of values increments by +1 every
`period` frames (with wrap-around at the channel's modulus).

Args:
    vals (np.ndarray): Sequence of integer values for a channel.
    width_bytes (int): Number of bytes used for this channel.
    period (int): Expected increment period in frames.

Returns:
    tuple[float, int]: Best match score in [0,1] and the phase offset.
"""

    if vals.size < 2:
        return 0.0, 0
    mod = 1 << (8 * width_bytes)
    steps = (np.diff(vals.astype(np.uint64)) % mod).astype(np.uint32)
    best_score, best_phase = -1.0, 0
    for phi in range(period):
        exp_plus1 = (np.arange(steps.size) % period) == phi
        good = ((steps == 1) & exp_plus1) | ((steps == 0) & ~exp_plus1)
        score = float(np.mean(good))
        if score > best_score:
            best_score, best_phase = score, phi
    return best_score, best_phase

def _auto_tail_counter(data: np.ndarray, frames: int) -> int:
    """Identify the most likely counter channel among tail channels.

    Examines channels 109–114 and scores them as simple (period=1) counters,
    returning the one with the best match.

    Args:
        data (np.ndarray): Channel × time array of processed samples.
        frames (int): Number of frames to evaluate.

    Returns:
        int: 1-based index of the best counter channel.
    """

    best_ch, best_score = None, -1.0
    for ch in range(109, 115):
        vals = data[ch - 1, :frames].astype(np.int64)
        score, _ = _score_periodic(vals, _chan_width_bytes(ch), period=1)
        if score > best_score:
            best_ch, best_score = ch, score
    return best_ch

def test_alignment(num, verbose=True, num_samples=default_num_samples, thresh_strict=0.98, thresh_periodic=0.95):
    """Run alignment test on a recorded raw buffer.

    Steps:
    1. Load buffer from file.
    2. Apply alignment correction using `offset_with_eeg`.
    3. Crop to a fixed number of frames.
    4. Process into channel × time arrays.
    5. Validate counters at key channels (37, 108, and tail auto-detected).

    Args:
        num (int): Buffer index (loads `./buffers/test_buffer{num}.bin`).
        verbose (bool, optional): Print per-channel debug info. Defaults to True.
        num_samples (int, optional): Maximum frames to check. Defaults to 4000.
        thresh_strict (float, optional): Minimum score for strict counters. Defaults to 0.98.
        thresh_periodic (float, optional): Minimum score for periodic counters. Defaults to 0.95.

    Returns:
        bool: True if all tested counters pass thresholds, False otherwise.

    Raises:
        ValueError: If no full frames remain after alignment.
    """

    # 1) load + align
    buffer = load_buffer(f'./buffers/test_buffer{num}.bin')
    offset = offset_with_eeg(buffer)
    if offset:
        buffer = buffer[:-offset]
    remainder = len(buffer) % tot_num_byte
    if remainder:
        buffer = buffer[remainder:]

    # 2) crop to last `frames`
    n_frames = len(buffer) // tot_num_byte
    if n_frames == 0:
        raise ValueError("No full frames after alignment.")
    frames = min(num_samples, n_frames)
    if n_frames > frames:
        buffer = buffer[-(tot_num_byte * frames):]

    # 3) process to channel x time
    temp_array = np.frombuffer(buffer, dtype=np.uint8)
    temp = np.reshape(temp_array, (-1, tot_num_byte)).T
    data = np.zeros((tot_num_chan, frames), dtype=np.float64)
    data = process(Config(False, True), temp, data, tot_num_byte, chan_ready=0)

    # 4) counters: 37 (period=1), 108 (period=4), tail auto (period=1)
    counters = [(37, 1), (108, 4)]
    tail_ch = _auto_tail_counter(data, frames)
    counters.append((tail_ch, 1))

    all_pass = True
    for ch, period in counters:
        vals = data[ch - 1, :frames].astype(np.int64)
        width = _chan_width_bytes(ch)
        score, phase = _score_periodic(vals, width, period=period)
        ok = score >= (thresh_periodic if period > 1 else thresh_strict)

        if print_slice:
            mod = 1 << (8 * width)
            sl = vals[slice_start:slice_start + slice_length]
            diffs = ((np.diff(sl) % mod) if sl.size >= 2 else np.array([], dtype=int)).tolist()
            if verbose: print(f"ch {ch} (w{width}B, period={period}, phase={phase}): "
                  f"slice {sl.tolist()}  diffs {diffs}  score={score:.3f}  PASS={ok}")

        all_pass &= ok

    print(f"[buffer {num}] offset={offset}, frames={frames}, tail_counter={tail_ch}, ALL_PASS={all_pass}")
    return all_pass

# Example:
if __name__ == "__main__":
    """Run alignment validation across multiple test buffers.

    Iterates over 20 test buffers and reports how many pass the counter checks,
    along with runtime.
    """

    passed = 0
    total = 20
    start = time.time()
    for i in range(total):
        if test_alignment(i+1, verbose=False):
            passed +=1
    print(f"BUFFER WAS CORRECTLY ALIGNED FOR {passed}/{total} TEST CASES in {time.time() - start:.3f} seconds")
