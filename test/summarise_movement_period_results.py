#!/usr/bin/env python3
import os, re
import numpy as np
import pandas as pd
from tabulate import tabulate

TABLES_DIR = r"./movement_period_eval/tables"
OUT_CSV    = os.path.join(TABLES_DIR, "metrics_by_time.csv")

# Which metrics to show in the printed summary if present
KEYS_TO_SHOW = ["precision","recall","f1","IoU","accuracy",
                "onset_err_ms","offset_err_ms","lag_ms","lag_ms_sd"]  # lag_ms_sd = jitter

def parse_time_ms(filename: str) -> int | None:
    m = re.search(r"(\d+)\s*ms", filename.lower())
    return int(m.group(1)) if m else None

def ci95(x: np.ndarray) -> tuple[float,float]:
    x = x.astype(float)
    x = x[~np.isnan(x)]
    n = x.size
    if n == 0: return (np.nan, np.nan)
    mean = float(np.mean(x))
    sd = float(np.std(x, ddof=1)) if n > 1 else 0.0
    half = 1.96 * sd / np.sqrt(n) if n > 1 else 0.0
    return (mean - half, mean + half)

def _normalise_columns(series: pd.Series) -> dict:
    """
    Convert one-row Series into a dict of numeric metrics:
    - *_mean -> base name (strip '_mean')
    - *_sd   -> keep as '<base>_sd'  (e.g., 'lag_ms_sd' = jitter)
    - other numeric columns -> keep as-is
    Non-numeric entries are ignored.
    """
    out = {}
    for col, val in series.items():
        # coerce to numeric if possible
        try:
            v = pd.to_numeric(val)
        except Exception:
            continue
        if pd.isna(v):
            continue

        if col.endswith("_mean"):
            base = col[:-5]
            out[base] = float(v)
        elif col.endswith("_sd"):
            out[col] = float(v)  # keep sd suffix
        else:
            # keep any other numeric column as-is
            out[col] = float(v)
    return out

def main():
    rows = []
    for fname in sorted(os.listdir(TABLES_DIR)):
        if not fname.lower().endswith(".csv"):
            continue
        t = parse_time_ms(fname)
        if t is None:
            continue

        df = pd.read_csv(os.path.join(TABLES_DIR, fname))
        if df.empty:
            continue

        # take first row (your files look like single-row summaries)
        one = df.iloc[0]
        metrics = _normalise_columns(one)
        if not metrics:
            continue
        metrics["time_ms"] = t
        rows.append(metrics)

    if not rows:
        print("No matching CSVs found in:", TABLES_DIR)
        return

    df_all = pd.DataFrame(rows)

    # Group by time and compute per-metric means
    by_time = df_all.groupby("time_ms", as_index=False).mean(numeric_only=True)

    # Build CI columns for every numeric metric
    records = []
    for t, g in df_all.groupby("time_ms"):
        rec = {"time_ms": t, "n_files": len(g)}
        for col in by_time.columns:
            if col == "time_ms":
                continue
            # mean across files for this time
            mean_val = by_time.loc[by_time["time_ms"] == t, col].values[0]
            rec[col] = mean_val
            # CI across files for this time
            lo, hi = ci95(g[col].to_numpy(dtype=float))
            rec[f"{col}_ci95_lo"] = lo
            rec[f"{col}_ci95_hi"] = hi
        records.append(rec)

    out = pd.DataFrame(records).sort_values("time_ms")
    out.to_csv(OUT_CSV, index=False)
    print("Saved by-time metrics (+95% CI) ->", OUT_CSV)

    # Pretty print a compact summary (means only) for key metrics that exist
    present_keys = [k for k in KEYS_TO_SHOW if k in out.columns]
    show_cols = ["time_ms","n_files"] + present_keys
    view = out[show_cols].copy()
    for c in present_keys:
        view[c] = view[c].map(lambda v: np.nan if pd.isna(v) else round(v, 3))
    print("\n=== Averages by prompt duration ===")
    print(tabulate(view, headers="keys", tablefmt="github"))

if __name__ == "__main__":
    main()
