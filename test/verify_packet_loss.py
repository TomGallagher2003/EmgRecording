#!/usr/bin/env python3
"""
Packet-loss for SyncStation sample counter only (no CLI args).
- De-dupes file listing (Windows-safe).
- Auto-detects SyncStation column by name, else by "counter-like" diffs.
- Auto-derives expected stride from mode of small positive diffs.
"""

import os
import math
import csv
import numpy as np
from glob import glob
from collections import Counter

# ======== CONFIG (edit if needed) ========
ROOT_DIR = "./test_recordings/counter_recordings"
HAS_HEADER = True  # set False if there is definitely no header line
MODULO = 65536     # 16-bit rollover
# Try these header names first (case-insensitive, substrings allowed)
SYNC_COL_CANDIDATES = [
    "syncstation", "sync", "ss", "ss_counter", "sync_counter",
    "sample_counter", "syncstation_counter", "sync station"
]
# ========================================


def _dedup_paths(paths):
    # Normalize case & resolve to avoid duplicates on Windows
    seen = set()
    out = []
    for p in paths:
        key = os.path.normcase(os.path.abspath(p))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return sorted(out)


def find_csvs(root: str):
    paths = []
    for ext in ("*.csv", "*.CSV"):
        paths.extend(glob(os.path.join(root, "**", ext), recursive=True))
    return _dedup_paths(paths)


def read_csv_header_and_matrix(path: str, has_header: bool):
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        header = None
        rows = []
        first = next(reader, None)
        if first is None:
            return None, np.empty((0, 0))

        # Heuristic: detect header if configured or if any token is non-numeric
        def is_numeric(tok: str) -> bool:
            try:
                float(tok)
                return True
            except ValueError:
                return False

        looks_like_header = has_header or any(not is_numeric(t) for t in first)
        if looks_like_header:
            header = [h.strip() for h in first]
        else:
            rows.append([t.strip() for t in first])

        for r in reader:
            rows.append([t.strip() for t in r])

    if not rows and header is not None:
        return header, np.empty((0, len(header)), dtype=np.float64)

    # Convert to float, coerce errors to NaN
    max_len = max((len(r) for r in rows), default=0)
    arr = np.full((len(rows), max_len), np.nan, dtype=np.float64)
    for i, r in enumerate(rows):
        for j, tok in enumerate(r):
            if j >= max_len:
                break
            try:
                arr[i, j] = float(tok)
            except ValueError:
                arr[i, j] = np.nan
    return header, arr


def find_sync_col_by_name(header):
    if not header:
        return None
    lower = [h.lower() for h in header]
    for cand in SYNC_COL_CANDIDATES:
        c = cand.lower()
        for idx, h in enumerate(lower):
            if h == c or c in h:
                return idx
    return None


def pick_counter_like_column(matrix: np.ndarray) -> int | None:
    """
    Choose the column that behaves most like a rolling counter:
    - minimal NaNs,
    - diffs have a clear small positive mode (after MODULO).
    """
    if matrix.size == 0:
        return None

    best_idx = None
    best_score = -1.0

    for j in range(matrix.shape[1]):
        col = matrix[:, j]
        col = col[~np.isnan(col)]
        if col.size < 4:
            continue

        diffs = (np.diff(col.astype(np.int64)) % MODULO)
        if diffs.size == 0:
            continue

        # focus on small forward diffs (no wraps, no zeros)
        small = diffs[(diffs > 0) & (diffs < (MODULO // 2))]
        if small.size == 0:
            continue

        # mode of small diffs
        counts = Counter(small.tolist())
        mode_diff, mode_cnt = counts.most_common(1)[0]

        # score: prefer strong unimodal small diff and low NaNs
        nan_penalty = 1.0 - (col.size / matrix.shape[0])  # 0 if full, >0 if many NaNs
        score = (mode_cnt / small.size) - nan_penalty
        if score > best_score:
            best_score = score
            best_idx = j

    return best_idx


def derive_expected_stride(counter: np.ndarray) -> int:
    diffs = (np.diff(counter.astype(np.int64)) % MODULO)
    small = diffs[(diffs > 0) & (diffs < (MODULO // 2))]
    if small.size == 0:
        # fallback: if all zeros, stride 1 (won’t matter); if wraps only, also 1
        return 1
    mode_diff, _ = Counter(small.tolist()).most_common(1)[0]
    return int(mode_diff)


def continuity_missing_only(counter: np.ndarray, expected_stride: int, modulo: int = MODULO):
    diffs = (np.diff(counter.astype(np.int64)) % modulo)
    missing = dups = resets = corrupt = 0
    repeat_streak = 0

    for d in diffs:
        if d == expected_stride:
            repeat_streak = 0
        elif d == 0:
            repeat_streak += 1
            # dups are informative only; not part of packet-loss calc
        elif d < (modulo // 2):  # forward jump, no wrap
            if d % expected_stride == 0:
                missing += (d // expected_stride) - 1
            else:
                corrupt += 1
            repeat_streak = 0
        else:  # wrap/reset
            resets += 1
            repeat_streak = 0
    return int(missing), int(dups), int(resets), int(corrupt)


def packet_loss_rate(missing: int, total_rows: int) -> float:
    return (missing / float(total_rows)) * 100.0 if total_rows > 0 else math.nan


def main():
    files = find_csvs(ROOT_DIR)
    if not files:
        print(f"No CSVs found under {ROOT_DIR}")
        return

    grand_missing = 0
    grand_rows = 0
    printed = 0

    for f in files:
        try:
            header, matrix = read_csv_header_and_matrix(f, HAS_HEADER)
            if matrix.size == 0 or matrix.shape[0] < 2:
                continue

            # Choose column: by name first, else by behavior
            idx = find_sync_col_by_name(header) if header else None
            if idx is None:
                idx = pick_counter_like_column(matrix)
            if idx is None:
                print(f"{os.path.basename(f)} -> ERROR: could not identify a counter-like column")
                continue

            col = matrix[:, idx]
            col = col[~np.isnan(col)]
            if col.size < 2:
                print(f"{os.path.basename(f)} -> ERROR: not enough numeric rows in chosen column")
                continue

            # Auto-derive stride to avoid bogus 12k% numbers when stride≠1
            stride = derive_expected_stride(col)

            missing, dups, resets, corrupt = continuity_missing_only(col, expected_stride=stride)
            loss_pct = packet_loss_rate(missing, col.size)

            print(
                f"{os.path.basename(f)} -> {loss_pct:.4f}% packet loss "
                f"(missing={missing}, rows={col.size}, dups={dups}, resets={resets}, corrupt={corrupt}) "
                f"[col={idx}{' '+header[idx] if header and 0 <= idx < len(header) else ''}; stride≈{stride}]"
            )

            grand_missing += missing
            grand_rows += col.size
            printed += 1

        except Exception as e:
            print(f"{os.path.basename(f)} -> ERROR: {e}")

    if printed > 0:
        overall = packet_loss_rate(grand_missing, grand_rows)
        print(f"\nOverall ----> {overall:.4f}% packet loss in {grand_rows} rows across {printed} files")


if __name__ == "__main__":
    main()
