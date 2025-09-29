#!/usr/bin/env python3
"""
verify_movement_period.py (simple, label-as-vector) + plotting

- Set DATA_DIR and FS inside main()
- Expects pairs in DATA_DIR:
    emg_data_*.csv   -> EMG matrix (channels x samples OR samples x channels)
    emg_label_*.csv  -> per-sample binary vector (length == samples), values {0,1}
- Runs detect_movement_mask() to get predicted binary mask
- Compares predicted mask to label mask with per-sample metrics
- Prints compact table + summary
- NEW: saves a plot per file showing aggregate EMG with vertical lines at
       label starts (green) and label ends (red), and predicted starts (blue)
       and predicted ends (orange). Also shades predicted mask.
"""

import os
import numpy as np
import pandas as pd
from tabulate import tabulate

from util import movement_segmentation
detect_movement_mask = movement_segmentation.detect_movement_mask

import matplotlib.pyplot as plt


def load_emg_csv(path: str) -> np.ndarray:
    X = pd.read_csv(path, header=None).values.astype(float)
    if X.ndim == 1:
        X = X[None, :]
    if X.shape[0] > X.shape[1]:
        X = X.T
    return X


def load_label_vector(path: str, expected_len: int | None = None) -> np.ndarray:
    df = pd.read_csv(path, header=None)
    arr = df.values
    if arr.ndim == 1:
        y = arr
    elif arr.shape[0] == 1:
        y = arr[0]
    elif arr.shape[1] == 1:
        y = arr[:, 0]
    else:
        y = arr.flatten()
    y = pd.to_numeric(pd.Series(y), errors='coerce').fillna(0).astype(int).values
    y = (y != 0).astype(np.uint8)
    if expected_len is not None and len(y) != expected_len:
        raise ValueError(f"Label length {len(y)} != samples {expected_len} in {os.path.basename(path)}")
    return y


def per_sample_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = y_true.astype(bool)
    y_pred = y_pred.astype(bool)
    tp = int(np.sum(y_true & y_pred))
    fp = int(np.sum(~y_true & y_pred))
    fn = int(np.sum(y_true & ~y_pred))
    tn = int(np.sum(~y_true & ~y_pred))
    total = tp + fp + fn + tn
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    acc = (tp + tn) / total if total > 0 else 0.0
    return {
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "IoU": iou,
        "accuracy": acc,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def mask_to_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    segs = []
    i, N = 0, mask.size
    while i < N:
        if mask[i]:
            j = i
            while j < N and mask[j]:
                j += 1
            segs.append((i, j))
            i = j
        else:
            i += 1
    return segs


def plot_emg_with_labels(fname: str, X: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, fs: float, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    N = X.shape[1]
    t = np.arange(N) / fs
    agg = np.mean(np.abs(X), axis=0)
    if np.max(agg) > 0:
        agg = agg / np.max(agg)

    true_segs = mask_to_segments(y_true)
    pred_segs = mask_to_segments(y_pred)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, agg, label='|EMG| (mean across channels)')

    # Shade predicted regions
    for s, e in pred_segs:
        ax.axvspan(t[s], t[e-1] if e>0 else t[e], alpha=0.15, color='tab:blue', label='_pred_span')

    # Label starts/ends
    for idx, (s, e) in enumerate(true_segs):
        ax.axvline(t[s], color='green', linestyle='-', linewidth=1.2, label='label start' if idx == 0 else None)
        ax.axvline(t[e-1] if e>0 else t[e], color='red', linestyle='-', linewidth=1.2, label='label end' if idx == 0 else None)

    # Pred starts/ends
    for idx, (s, e) in enumerate(pred_segs):
        ax.axvline(t[s], color='tab:blue', linestyle='--', linewidth=1.0, label='pred start' if idx == 0 else None)
        ax.axvline(t[e-1] if e>0 else t[e], color='tab:orange', linestyle='--', linewidth=1.0, label='pred end' if idx == 0 else None)

    ax.set_title(fname)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Normalized amplitude')
    ax.legend(loc='upper right', ncol=4, fontsize=8)
    ax.grid(True, alpha=0.3)

    out_path = os.path.join(out_dir, os.path.splitext(fname)[0] + ".png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

def estimate_lag_ms(y_true: np.ndarray, y_pred: np.ndarray, fs: float, max_lag_ms: int = 500) -> tuple[int, float]:
    """Lag of pred relative to label via bounded cross-corr. +ve => pred late."""
    y_true = y_true.astype(np.float32); y_pred = y_pred.astype(np.float32)
    a = y_true - y_true.mean(); b = y_pred - y_pred.mean()
    L = int(round(max_lag_ms * fs / 1000.0))
    best_corr, best_k = -np.inf, 0
    for k in range(-L, L + 1):
        if k >= 0:
            a_win, b_win = a[k:], b[:len(a) - k]
        else:
            a_win, b_win = a[:k], b[-k:]
        if a_win.size:
            c = float(np.dot(a_win, b_win))
            if c > best_corr:
                best_corr, best_k = c, k
    return best_k, best_k * 1000.0 / fs

def shift_mask(mask: np.ndarray, lag_samples: int) -> np.ndarray:
    out = np.zeros_like(mask, dtype=mask.dtype); N = mask.size
    if lag_samples >= 0:
        out[lag_samples:] = mask[:N - lag_samples]
    else:
        out[:lag_samples] = mask[-lag_samples:]
    return out

def onset_offset_indices(x: np.ndarray):
    N = x.size
    # onset
    if x[0] == 1:
        s = 0
    else:
        s = next((i for i in range(1, N) if x[i-1] == 0 and x[i] == 1), None)
    # offset
    if x[-1] == 1:
        e = N
    else:
        e = next((i for i in range(N-1, 0, -1) if x[i-1] == 1 and x[i] == 0), None)
    return s, e


def per_sample_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = y_true.astype(bool); y_pred = y_pred.astype(bool)
    tp = int(np.sum(y_true & y_pred)); fp = int(np.sum(~y_true & y_pred))
    fn = int(np.sum(y_true & ~y_pred)); tn = int(np.sum(~y_true & ~y_pred))
    total = tp + fp + fn + tn
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    acc = (tp + tn) / total if total > 0 else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "IoU": iou, "accuracy": acc,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def main():
    DATA_DIR = "test_recordings/emg_data_only/test_A/csv"  # <- set your folder here
    FS = 2000.0           # sampling rate (Hz)
    PLOTS_DIR = "./movement_period_plots/test_A" # output folder for images

    rows = []
    metrics_list = []
    lag_ms_list, on_err_list, off_err_list = [], [], []
    iou_raw_list, iou_aligned_list = [], []

    ALIGN_METHOD = "onset"  # or "xcorr"

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.startswith("emg_data_") or not fname.endswith(".csv"):
            continue
        data_path = os.path.join(DATA_DIR, fname)
        label_path = data_path.replace("emg_data_", "emg_label_")
        if not os.path.exists(label_path):
            print(f"[WARN] no label file for {fname}")
            continue

        X = load_emg_csv(data_path)
        y_pred = detect_movement_mask(X, FS, single_segment=True)
        y_true = load_label_vector(label_path, expected_len=y_pred.size)

        # --- RAW METRICS (defines m) ---
        m = per_sample_metrics(y_true, y_pred)
        iou_raw_list.append(m["IoU"])

        # --- Onset/offset indices + onset/offset errors ---
        ls, le = onset_offset_indices(y_true)
        ps, pe = onset_offset_indices(y_pred)
        on_err_ms = None if (ls is None or ps is None) else (ps - ls) * 1000.0 / FS
        off_err_ms = None if (le is None or pe is None) else (pe - le) * 1000.0 / FS

        # --- Lag estimate + aligned IoU ---
        if ALIGN_METHOD == "xcorr":
            lag_samp, lag_ms = estimate_lag_ms(y_true, y_pred, FS, max_lag_ms=500)
        else:
            # onset-based lag (more stable for single segment)
            if (ls is not None) and (ps is not None):
                lag_samp = ps - ls
                lag_ms = lag_samp * 1000.0 / FS
            else:
                lag_samp, lag_ms = 0, 0.0  # fallback if edges missing

        y_pred_aligned = shift_mask(y_pred, -lag_samp)
        m_aligned = per_sample_metrics(y_true, y_pred_aligned)

        # --- Append ALL sync stats (prevents NaNs) ---
        lag_ms_list.append(lag_ms)
        on_err_list.append(on_err_ms)
        off_err_list.append(off_err_ms)
        iou_aligned_list.append(m_aligned["IoU"])

        # --- Table row ---
        rows.append([
            fname,
            int(m["tp"]), int(m["fp"]), int(m["fn"]), int(m["tn"]),
            m["precision"], m["recall"], m["f1"], m["IoU"], m["accuracy"],
        ])
        metrics_list.append(m)

        # --- Plot ---
        try:
            plot_emg_with_labels(fname, X, y_true, y_pred, FS, PLOTS_DIR)
        except Exception as e:
            print(f"[WARN] plotting failed for {fname}: {e}")

    headers = [
        "file", "tp", "fp", "fn", "tn", "precision", "recall", "f1", "IoU", "accuracy"
    ]

    if rows:
        print("\n=== Movement Period Verification (per-sample) ===")
        print(tabulate(rows, headers=headers, tablefmt="github", floatfmt=".3f"))
        df = pd.DataFrame(metrics_list)
        print("\nSummary:")
        print("precision=%.3f recall=%.3f f1=%.3f IoU=%.3f accuracy=%.3f" % (
            df["precision"].mean(), df["recall"].mean(), df["f1"].mean(), df["IoU"].mean(), df["accuracy"].mean()
        ))
        print(f"\nSaved plots -> {os.path.abspath(PLOTS_DIR)}")
    else:
        print("No matching emg_data_/emg_label_ pairs found.")

    def _nanmean(x):
        x = np.array([v for v in x if v is not None], dtype=float)
        return float(np.nanmean(x)) if x.size else float('nan')

    def _nanstd(x):
        x = np.array([v for v in x if v is not None], dtype=float)
        return float(np.nanstd(x)) if x.size else float('nan')

    def _ci95_mean(x):
        x = np.array([v for v in x if v is not None], dtype=float)
        n = x.size
        if n == 0: return (float('nan'), float('nan'))
        m = float(np.mean(x));
        s = float(np.std(x, ddof=1)) if n > 1 else 0.0
        half = 1.96 * s / np.sqrt(n) if n > 1 else 0.0
        return (m - half, m + half)

    mean_lag, sd_lag = _nanmean(lag_ms_list), _nanstd(lag_ms_list)
    mean_on, sd_on = _nanmean(on_err_list), _nanstd(on_err_list)
    mean_off, sd_off = _nanmean(off_err_list), _nanstd(off_err_list)
    ci_lag = _ci95_mean(lag_ms_list)

    mean_iou_raw = float(np.mean(iou_raw_list)) if iou_raw_list else float('nan')
    mean_iou_aln = float(np.mean(iou_aligned_list)) if iou_aligned_list else float('nan')
    delta_iou = mean_iou_aln - mean_iou_raw

    print("\n=== Sync Summary ===")
    print(f"lag_ms: mean={mean_lag:.1f} SD={sd_lag:.1f}  95%CI=({ci_lag[0]:.1f},{ci_lag[1]:.1f})")
    print(f"onset_error_ms:  mean={mean_on:.1f} SD={sd_on:.1f}")
    print(f"offset_error_ms: mean={mean_off:.1f} SD={sd_off:.1f}")
    print(f"IoU raw={mean_iou_raw:.3f}  aligned={mean_iou_aln:.3f}  ΔIoU={delta_iou:+.3f}")


if __name__ == "__main__":
    main()