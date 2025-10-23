#!/usr/bin/env python3
"""
Clock-sync audit for EMG/EEG counter CSVs.

Replaces the old "packet loss" checks with robust synchronisation metrics:
- Assumes 3 columns: [SYNC, EMG, EEG] counters (16-bit, modulo 65536).
- EEG is sampled at 1/4 of EMG (EEG_REPEAT=4). Hence, EEG counter should
  increment once every 4 EMG rows.
- We detect EEG increments (diff == 1 mod 2^16), segment files at resets,
  and compute the stride (#rows between EEG increments), phase, and drift.

Outputs a per-file table:
  file | rows | eeg_incs | stride_mean | stride_std | stride_min | stride_max
       | phase_mode | ratio_rows_per_eeg_inc | drift_ppm | segments | notes

Where:
- stride_* describe the distribution of row distances between consecutive EEG increments
  within continuous (no-reset) segments.
- phase_mode is the most common value of (EEG increment row index mod EEG_REPEAT).
- ratio_rows_per_eeg_inc ≈ 4 when clocks are aligned and no increments were missed.
- drift_ppm = ((stride_mean / EEG_REPEAT) - 1) * 1e6 (parts per million).

If a file contains resets, metrics are computed per segment and then aggregated;
“segments” shows how many continuous stretches were seen.
"""

import os
import glob
import numpy as np
from collections import Counter

# ================== CONFIG ==================
DATA_DIR    = "./test_recordings/counter_recordings/3/counters/EB/csv"
FILE_GLOB   = "counters_data_*.csv"
MOD         = 2**16
EEG_REPEAT  = 4                 # EMG:EEG expected stride ratio = 4
RESET_CUTOFF = MOD // 2         # per-step diff >= this ⇒ reset boundary
# ============================================

def load_csv_three_cols(path: str) -> np.ndarray:
    """
    Load a CSV as int64, take the first 3 columns.
    For robustness, use genfromtxt which tolerates minor ragged rows.
    """
    arr = np.genfromtxt(path, delimiter=",", dtype=np.int64)
    if arr.ndim == 1:
        # Single-row or single-col: reshape defensively
        arr = np.atleast_2d(arr)
    if arr.shape[1] < 3:
        raise ValueError(f"{os.path.basename(path)}: expected ≥3 columns, got {arr.shape[1]}")
    return arr[:, :3]

def modulo_diff(x: np.ndarray) -> np.ndarray:
    """Forward diffs modulo 2^16."""
    return (np.diff(x) % MOD).astype(np.int64)

def segment_by_resets(diffs_mod: np.ndarray):
    """
    Given per-step diffs (len N-1), return list of (start_idx, end_idx_excl) in row indices.
    Segment breaks where diffs_mod[i] >= RESET_CUTOFF.
    """
    N = diffs_mod.size + 1
    if N <= 1:
        return [(0, N)]
    cut_idx = np.where(diffs_mod >= RESET_CUTOFF)[0]
    segs, s = [], 0
    for i in cut_idx:
        segs.append((s, i + 1))  # rows [s .. i], diffs [s .. i-1]
        s = i + 1
    segs.append((s, N))
    return segs

def eeg_increment_rows(eeg: np.ndarray):
    """
    Find row indices where EEG counter increments by +1 (mod 2^16).
    Returns a tuple: (indices array, segments list)
    - indices are absolute row indices in the file (0..N-1).
    - segments are (start_row, end_row_exclusive) continuous stretches w/o resets.
    """
    d = modulo_diff(eeg)
    segs = segment_by_resets(d)
    inc_rows = []
    for (s, e) in segs:
        if e - s <= 1:
            continue
        # within segment, mark rows where diff == 1; add +1 to map diff idx -> row idx
        inc = np.where(d[s:e-1] == 1)[0] + (s + 1)
        if inc.size:
            inc_rows.append(inc)
    if inc_rows:
        inc_rows = np.concatenate(inc_rows)
    else:
        inc_rows = np.empty((0,), dtype=np.int64)
    return inc_rows, segs

def stride_stats_from_inc_rows(inc_rows: np.ndarray, segs):
    """
    Compute stride (rows between consecutive EEG increments) within each segment.
    Returns:
      strides_all (np.ndarray)  : concatenated strides across segments
      phase_counts (Counter)    : histogram of (inc_row % EEG_REPEAT)
      segments_with_incs (int)  : number of segments that contributed
    """
    strides_all = []
    phase_counts = Counter()
    contributing = 0
    for (s, e) in segs:
        # extract increment rows in this segment
        seg_inc = inc_rows[(inc_rows >= s) & (inc_rows < e)]
        if seg_inc.size >= 2:
            contributing += 1
            seg_strides = np.diff(seg_inc)  # row deltas; expect ~ EEG_REPEAT
            strides_all.append(seg_strides)
        if seg_inc.size > 0:
            phase_counts.update((seg_inc % EEG_REPEAT).tolist())
    if strides_all:
        strides_all = np.concatenate(strides_all)
    else:
        strides_all = np.empty((0,), dtype=np.int64)
    return strides_all, phase_counts, contributing

def safe_mean_std(arr: np.ndarray):
    if arr.size == 0:
        return (np.nan, np.nan)
    return (float(np.mean(arr)), float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0)

def analyze_file(path: str):
    data = load_csv_three_cols(path)
    rows = data.shape[0]
    sync, emg, eeg = data[:, 0], data[:, 1], data[:, 2]

    # Find EEG increment rows and segments
    inc_rows, segs = eeg_increment_rows(eeg)

    # Stride stats (rows between consecutive EEG increments)
    strides, phase_counts, seg_contrib = stride_stats_from_inc_rows(inc_rows, segs)

    # Global ratio (rows-1) / #EEG increments (should be ~4)
    eeg_incs = inc_rows.size
    ratio = (rows - 1) / eeg_incs if eeg_incs > 0 else np.nan

    # Mean & std of stride; drift in ppm relative to expected stride
    mean_stride, std_stride = safe_mean_std(strides)
    drift_ppm = ((mean_stride / EEG_REPEAT) - 1.0) * 1e6 if np.isfinite(mean_stride) else np.nan

    # Phase mode (most frequent inc row index mod EEG_REPEAT)
    phase_mode = None
    if phase_counts:
        phase_mode = phase_counts.most_common(1)[0][0]

    notes = []
    # sanity checks
    if eeg_incs == 0:
        notes.append("no EEG increments detected")
    if not np.isfinite(ratio):
        notes.append("ratio nan")
    if seg_contrib == 0 and eeg_incs > 0:
        notes.append("isolated increments (no consecutive incs per segment)")
    if std_stride is not None and np.isfinite(std_stride) and std_stride > 0.1:
        notes.append("stride jitter")

    return dict(
        file=os.path.basename(path),
        rows=rows,
        eeg_incs=int(eeg_incs),
        stride_mean=None if not np.isfinite(mean_stride) else round(mean_stride, 3),
        stride_std=None if not np.isfinite(std_stride) else round(std_stride, 3),
        stride_min=None if strides.size == 0 else int(np.min(strides)),
        stride_max=None if strides.size == 0 else int(np.max(strides)),
        phase_mode=phase_mode,
        ratio_rows_per_eeg_inc=None if not np.isfinite(ratio) else round(ratio, 6),
        drift_ppm=None if not np.isfinite(drift_ppm) else round(drift_ppm, 2),
        segments=len(segs),
        segments_with_increments=seg_contrib,
        notes="; ".join(notes) if notes else ""
    )

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, FILE_GLOB)))
    if not files:
        print(f"No files found in {os.path.abspath(DATA_DIR)} matching {FILE_GLOB}")
        return

    results = []
    for p in files:
        try:
            results.append(analyze_file(p))
        except Exception as e:
            print(f"[WARN] {os.path.basename(p)}: {e}")

    # Pretty print
    headers = [
        "file","rows","eeg_incs",
        "stride_mean","stride_std","stride_min","stride_max",
        "phase_mode","ratio_rows_per_eeg_inc","drift_ppm",
        "segments","segments_with_increments","notes"
    ]
    try:
        from tabulate import tabulate
        print("\n=== EMG↔EEG Clock Sync Audit (EEG increments & stride @ EMG-rate) ===")
        print(tabulate([[r.get(h, "") for h in headers] for r in results], headers=headers, tablefmt="github"))
    except Exception:
        # Fallback CSV print
        print(",".join(headers))
        for r in results:
            print(",".join(str(r.get(h, "")) for h in headers))

    # Summary across files (only include files that had usable strides)
    valid = [r for r in results if isinstance(r.get("stride_mean"), (int, float))]
    if valid:
        all_strides = []
        for r in valid:
            # we didn't store per-file arrays, but the aggregate indicators are enough for summary:
            pass
        means = [r["stride_mean"] for r in valid if r["stride_mean"] is not None]
        stds  = [r["stride_std"] for r in valid if r["stride_std"] is not None]
        ratios = [r["ratio_rows_per_eeg_inc"] for r in valid if r["ratio_rows_per_eeg_inc"] is not None]
        drifts = [r["drift_ppm"] for r in valid if r["drift_ppm"] is not None]

        def fmean(xs): return float(np.mean(xs)) if xs else float("nan")
        def fstd(xs):  return float(np.std(xs, ddof=1)) if len(xs) > 1 else 0.0

        print("\nSummary across files (where strides were measurable):")
        print(f"- stride_mean avg = {fmean(means):.4f} (target {EEG_REPEAT})")
        print(f"- stride_std  avg = {fmean(stds):.4f}")
        print(f"- ratio_rows_per_eeg_inc avg = {fmean(ratios):.6f}")
        print(f"- drift_ppm avg = {fmean(drifts):.2f}, std = {fstd(drifts):.2f}")
    else:
        print("\nSummary: no measurable strides (no consecutive EEG increments).")

if __name__ == "__main__":
    main()
