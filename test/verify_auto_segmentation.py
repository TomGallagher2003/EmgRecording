#!/usr/bin/env python3
"""
Verify auto segmentation vs Ninapro DB1 labels (single CSV, overall metrics only).

- Edit CONFIG below (CSV_PATH, FS, etc.)
- Treats Ninapro labels as the REFERENCE and evaluates your auto-segmentation.
- Outputs:
  - Console: overall metrics table
  - CSV: overall_metrics.csv
  - Optional: one diagnostic plot (aggregate |EMG| with reference vs segmentation)

Assumptions:
- Columns (case-insensitive): serial, 10 emg*, 22 CyberGlove*, exercise, stimulus, restimulus,
  repetition, rerepetition, subject. (Headers are auto-normalized to lowercase.)
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

# ===================== CONFIG (EDIT ME) =====================

CSV_PATH       = r"Ninapro_data/db_1/Ninapro_DB1.csv"  # whole DB1 CSV
FS             = 1000.0                                 # EMG sampling rate (Hz)
PLOTS_DIR      = r"./auto_seg_eval_outputs/plots"       # where to save the plot
TABLES_DIR     = r"./auto_seg_eval_outputs/tables"      # where to save the CSV
REF_PREFERRED  = "restimulus"                           # preferred reference column
MAKE_PLOT      = False                                    # save one overall plot
SINGLE_SEGMENT = False                                   # pass through to  detector

# ============================================================

# detector
from util import movement_segmentation
DETECT = movement_segmentation.detect_movement_mask  # DETECT(X, FS, single_segment=...)

# ---------------------- helpers -----------------------------

def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def load_db1_csv(path: str, emg_cols=None):
    df = pd.read_csv(path)
    df = norm_cols(df)

    # Meta columns (optional if missing)
    meta_keys = ["serial", "exercise", "stimulus", "restimulus",
                 "repetition", "rerepetition", "subject"]
    meta = {k: (df[k].values if k in df.columns else None) for k in meta_keys}

    # EMG columns: prefer those starting with 'emg'
    if emg_cols is None:
        emg_cols = [c for c in df.columns if c.startswith("emg")][:10]
        if len(emg_cols) < 10 and "serial" in df.columns:
            cols = df.columns.tolist()
            sidx = cols.index("serial")
            emg_cols = cols[sidx+1: sidx+1+10]
    if len(emg_cols) != 10:
        raise ValueError(f"Expected 10 EMG columns; found {len(emg_cols)} -> {emg_cols}")

    X_all = df[emg_cols].values.astype(np.float32).T  # (10, N)
    meta["df"] = df
    meta["emg_cols"] = emg_cols
    return X_all, meta

def build_reference_mask(meta, preferred="restimulus") -> np.ndarray:
    """
    Try 'preferred' column first; if absent, fall back to the other one.
    Marks movement as value > 0.
    """
    preferred = preferred.lower()
    options = [preferred, "stimulus" if preferred == "restimulus" else "restimulus"]
    for col in options:
        vec = meta.get(col)
        if vec is not None:
            return (vec.astype(float) > 0).astype(np.uint8), col
    raise KeyError("Neither 'restimulus' nor 'stimulus' found in CSV.")

def mask_to_segments(mask: np.ndarray):
    segs = []
    i, N = 0, mask.size
    while i < N:
        if mask[i]:
            j = i + 1
            while j < N and mask[j]:
                j += 1
            segs.append((i, j))
            i = j
        else:
            i += 1
    return segs

def onset_offset_indices(x: np.ndarray):
    N = x.size
    s = 0 if x[0]==1 else next((i for i in range(1, N) if x[i-1]==0 and x[i]==1), None)
    e = N if x[-1]==1 else next((i for i in range(N-1, 0, -1) if x[i-1]==1 and x[i]==0), None)
    return s, e

def per_sample_metrics(y_true: np.ndarray, y_pred: np.ndarray):
    y_true = y_true.astype(bool); y_pred = y_pred.astype(bool)
    tp = int(np.sum(y_true & y_pred)); fp = int(np.sum(~y_true & y_pred))
    fn = int(np.sum(y_true & ~y_pred)); tn = int(np.sum(~y_true & ~y_pred))
    total = tp + fp + fn + tn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = 2*prec*rec/(prec+rec) if (prec+rec) else 0.0
    iou  = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0
    acc  = (tp + tn) / total if total else 0.0
    return dict(precision=prec, recall=rec, f1=f1, IoU=iou, accuracy=acc, tp=tp, fp=fp, fn=fn, tn=tn)

def event_level_overlap(y_ref: np.ndarray, y_seg: np.ndarray) -> int:
    return int(np.any(y_ref.astype(bool) & y_seg.astype(bool)))

def plot_overall(title: str, X: np.ndarray, y_ref: np.ndarray, y_seg: np.ndarray, fs: float, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    N = X.shape[1]
    t = np.arange(N) / fs
    agg = np.mean(np.abs(X), axis=0)
    if np.max(agg) > 0:
        agg = agg / np.max(agg)

    ref_segs = mask_to_segments(y_ref)
    seg_segs = mask_to_segments(y_seg)

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(t, agg, label='|EMG| mean')

    # Shade predicted (segmentation)
    for s, e in seg_segs:
        ax.axvspan(t[s], t[e-1 if e>0 else e], alpha=0.15, label='_seg', color='tab:blue')

    # Reference start/end
    for k, (s, e) in enumerate(ref_segs):
        ax.axvline(t[s], color='green', lw=1.2, label='ref start' if k==0 else None)
        ax.axvline(t[e-1 if e>0 else e], color='red', lw=1.2, label='ref end' if k==0 else None)

    # Segmentation start/end
    for k, (s, e) in enumerate(seg_segs):
        ax.axvline(t[s], color='tab:blue', ls='--', lw=1.0, label='seg start' if k==0 else None)
        ax.axvline(t[e-1 if e>0 else e], color='tab:orange', ls='--', lw=1.0, label='seg end' if k==0 else None)

    ax.set_title(title)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Normalized amplitude")
    ax.legend(loc='upper right', ncol=4, fontsize=8)
    ax.grid(True, alpha=0.3)
    out = out_dir / (Path(title).stem + ".png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

# ---------------------- main runner -------------------------

def run():
    Path(PLOTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(TABLES_DIR).mkdir(parents=True, exist_ok=True)

    # Load full CSV once
    X_all, meta = load_db1_csv(CSV_PATH)
    # Build reference; prefer restimulus, fall back to stimulus
    y_ref_all, ref_used = build_reference_mask(meta, preferred=REF_PREFERRED)

    # Run detector and compute overall metrics
    y_seg_all = DETECT(X_all, FS, single_segment=SINGLE_SEGMENT).astype(np.uint8)
    N = min(y_ref_all.size, y_seg_all.size)
    X = X_all[:, :N]
    y_ref = y_ref_all[:N]
    y_seg = y_seg_all[:N]

    m = per_sample_metrics(y_true=y_ref, y_pred=y_seg)
    rs, re = onset_offset_indices(y_ref)
    ss, se = onset_offset_indices(y_seg)
    onset_err_ms  = None if (rs is None or ss is None) else (rs - ss) * 1000.0 / FS
    offset_err_ms = None if (re is None or se is None) else (re - se) * 1000.0 / FS
    evt = event_level_overlap(y_ref, y_seg)

    print("\n=== OVERALL (segmentation vs Ninapro reference) ===")
    print(f"Reference column used: {ref_used}")
    print(tabulate([[m["precision"], m["recall"], m["f1"], m["IoU"], m["accuracy"], evt]],
                   headers=["precision","recall","f1","IoU","accuracy","event_overlap"],
                   tablefmt="github", floatfmt=".3f"))
    print("Onset error (labels - seg):", "n/a" if onset_err_ms is None else f"{onset_err_ms:.1f} ms")
    print("Offset error (labels - seg):", "n/a" if offset_err_ms is None else f"{offset_err_ms:.1f} ms")

    # Save overall CSV
    out_csv = Path(TABLES_DIR) / "overall_metrics.csv"
    pd.DataFrame([{
        "reference": ref_used,
        "precision": m["precision"], "recall": m["recall"], "f1": m["f1"], "IoU": m["IoU"],
        "accuracy": m["accuracy"], "event_overlap": evt,
        "onset_err_ms": onset_err_ms, "offset_err_ms": offset_err_ms
    }]).to_csv(out_csv, index=False)
    print(f"Saved overall metrics -> {out_csv.resolve()}")

    if MAKE_PLOT:
        plot_overall("overall", X, y_ref, y_seg, FS, Path(PLOTS_DIR))
        print(f"Saved plot -> {(Path(PLOTS_DIR) / 'overall.png').resolve()}")

if __name__ == "__main__":
    run()
