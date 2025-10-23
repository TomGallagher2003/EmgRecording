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
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    os.makedirs(out_dir, exist_ok=True)

    plt.rcParams.update({
        "font.size": 12,
        "axes.facecolor": "white",
        "figure.facecolor": "none",
        "axes.edgecolor": "none",
        "axes.labelcolor": "#0f172a",
        "xtick.color": "#0f172a",
        "ytick.color": "#0f172a",
        "axes.grid": False,
        "grid.color": (0, 0, 0, 0.08),
        "grid.linewidth": 1.0,
        "legend.frameon": False
    })

    # --- Use channel 12 (index 11) raw signal ---
    N = X.shape[1]
    t = np.arange(N) / fs
    ch_idx = 11  # channel 12 (0-indexed)
    emg_ch = X[ch_idx, :]

    true_segs = mask_to_segments(y_true)
    pred_segs = mask_to_segments(y_pred)

    fig, ax = plt.subplots(figsize=(12, 4.2))
    # Slide-matching palette (based on your showcase gradient)
    emg_col = "#ffffff"  # Cyan-blue (matches F1 bars)
    true_fill = "#0377fc"  # Soft mint green (matches Recall)
    pred_fill = "#fcfc03"  # Lavender-blue (complements background)
    pred_edge = "#ff0000"  # Deep indigo edge for contrast
    true_edge = "#000000"

    ax.plot(t, emg_ch, color=emg_col, linewidth=1.5, label=f"EMG channel {ch_idx+1}")

    # Compute vertical range dynamically for shading
    y_min, y_max = np.min(emg_ch), np.max(emg_ch)
    y_pad = 0.05 * (y_max - y_min)
    y_min -= y_pad
    y_max += y_pad

    # Shade true label regions
    for s, e in true_segs:
        x0, x1 = t[s], t[e - 1] if e > 0 else t[e]
        rect = Rectangle((x0, y_min), x1 - x0, y_max - y_min,
                         facecolor=true_fill, alpha=0.4,
                         edgecolor="none", linewidth=2)
        ax.add_patch(rect)

    # Shade predicted regions with faint edge
    for s, e in pred_segs:
        x0, x1 = t[s], t[e-1] if e > 0 else t[e]
        rect = Rectangle((x0, y_min), x1 - x0, y_max - y_min,
                         facecolor=pred_fill, alpha=0.4,
                         edgecolor="none", linewidth=2)
        ax.add_patch(rect)

    ax.set_xlabel("Time (s)", fontsize=20)
    ax.set_ylabel("Amplitude (raw)", fontsize=20)
    ax.set_ylim(y_min, y_max)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.margins(x=0.01)

    handles = [
        Rectangle((0, 0), 1, 1, facecolor=true_fill, alpha=0.4, edgecolor="none", label="Prompt label"),
        Rectangle((0, 0), 1, 1, facecolor=pred_fill, alpha=0.4, edgecolor="none", linewidth=1.2, label="Auto segmentation"),
    ]
    ax.legend(handles=handles, loc="upper right", ncol=3, fontsize=14)

    fig.tight_layout()
    out_path = os.path.join(out_dir, os.path.splitext(fname)[0] + ".png")
    fig.savefig(out_path, dpi=300, transparent=True)
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


def main(data_dir, plots_dir, csv_dir, outfile):
    DATA_DIR = data_dir
    FS = 2000.0           # sampling rate (Hz)
    PLOTS_DIR = plots_dir # output folder for images

    os.makedirs(csv_dir, exist_ok=True)  # ensure csv_dir exists

    rows = []
    metrics_list = []
    lag_ms_list, on_err_list, off_err_list = [], [], []
    iou_raw_list, iou_aligned_list = [], []

    ALIGN_METHOD = "onset"  # or "xcorr"

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.startswith("emg_data_") or not fname.endswith(".csv") or "rest" in fname:
            continue
        data_path = os.path.join(DATA_DIR, fname)
        label_path = data_path.replace("emg_data_", "emg_label_")
        if not os.path.exists(label_path):
            print(f"[WARN] no label file for {fname}")
            continue

        X = load_emg_csv(data_path)
        y_pred = detect_movement_mask(X, FS, single_segment=True)
        y_true = load_label_vector(label_path, expected_len=y_pred.size)

        # --- RAW METRICS ---
        m = per_sample_metrics(y_pred, y_true)
        iou_raw_list.append(m["IoU"])

        # --- Onset/offset errors ---
        ls, le = onset_offset_indices(y_pred)
        ps, pe = onset_offset_indices(y_true)
        on_err_ms = None if (ls is None or ps is None) else (ps - ls) * 1000.0 / FS
        off_err_ms = None if (le is None or pe is None) else (pe - le) * 1000.0 / FS

        # --- Lag + aligned IoU ---
        if ALIGN_METHOD == "xcorr":
            lag_samp, lag_ms = estimate_lag_ms(y_true, y_pred, FS, max_lag_ms=500)
        else:
            if (ls is not None) and (ps is not None):
                lag_samp = ps - ls
                lag_ms = lag_samp * 1000.0 / FS
            else:
                lag_samp, lag_ms = 0, 0.0
        y_pred_aligned = shift_mask(y_pred, -lag_samp)
        m_aligned = per_sample_metrics(y_true, y_pred_aligned)

        # --- Store sync stats ---
        lag_ms_list.append(lag_ms)
        on_err_list.append(on_err_ms)
        off_err_list.append(off_err_ms)
        iou_aligned_list.append(m_aligned["IoU"])

        # --- Per-file row ---
        rows.append([
            fname,
            int(m["tp"]), int(m["fp"]), int(m["fn"]), int(m["tn"]),
            m["precision"], m["recall"], m["f1"], m["IoU"], m["accuracy"],
            lag_ms, on_err_ms, off_err_ms, m_aligned["IoU"]
        ])
        metrics_list.append(m)

        # --- Plot ---
        try:
            plot_emg_with_labels(fname, X, y_true, y_pred, FS, PLOTS_DIR)
        except Exception as e:
            print(f"[WARN] plotting failed for {fname}: {e}")

    headers = [
        "file", "tp", "fp", "fn", "tn", "precision", "recall", "f1", "IoU", "accuracy",
        "lag_ms", "onset_err_ms", "offset_err_ms", "IoU_aligned"
    ]

    if rows:
        print("\n=== Movement Period Verification (per-sample) ===")
        print(tabulate(rows, headers=headers, tablefmt="github", floatfmt=".3f"))
        df = pd.DataFrame(rows, columns=headers)


        # Summary
        summary = {
            "precision_mean": df["precision"].mean(),
            "recall_mean": df["recall"].mean(),
            "f1_mean": df["f1"].mean(),
            "IoU_mean": df["IoU"].mean(),
            "accuracy_mean": df["accuracy"].mean(),
            "lag_ms_mean": np.nanmean(lag_ms_list),
            "lag_ms_sd": np.nanstd(lag_ms_list),
            "onset_err_ms_mean": np.nanmean(on_err_list),
            "offset_err_ms_mean": np.nanmean(off_err_list),
            "IoU_raw_mean": np.mean(iou_raw_list) if iou_raw_list else float('nan'),
            "IoU_aligned_mean": np.mean(iou_aligned_list) if iou_aligned_list else float('nan')
        }
        summary_path = os.path.join(csv_dir, f"{outfile}.csv")
        pd.DataFrame([summary]).to_csv(summary_path, index=False)
        print(f"Saved summary results -> {summary_path}")

        print("\nSummary:")
        print("precision=%.3f recall=%.3f f1=%.3f IoU=%.3f accuracy=%.3f" % (
            summary["precision_mean"], summary["recall_mean"], summary["f1_mean"],
            summary["IoU_mean"], summary["accuracy_mean"]
        ))
        print(f"\nSaved plots -> {os.path.abspath(PLOTS_DIR)}")
    else:
        print("No matching emg_data_/emg_label_ pairs found.")



if __name__ == "__main__":
    times = {"300ms" : "EA", "1000ms" : "EB", "3000ms" : "EA"}
    subjects = ["A", "B", "C"]
    for subject in subjects:
        for time, set in times.items():
            main(f"test_recordings/subject_{subject}/{time}_trial/emg/{set}/csv", f"movement_period_eval/plots/showcase", f"movement_period_eval/tables", f"subject_{subject}_{time}")